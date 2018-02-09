# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PointToPolygon
                                 A QGIS plugin
 Creates polygons around points
                              -------------------
        begin                : 2018-01-19
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Bruno Combal
        email                : bruno.combal@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog
from qgis.core import *
from osgeo import ogr
import os

# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from pointtopolygon_dialog import PointToPolygonDialog
import os.path
import math
from polygonBuffer import doPolygon

class PointToPolygon:
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'PointToPolygon_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Point to Polygon')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'PointToPolygon')
        self.toolbar.setObjectName(u'PointToPolygon')

        # business variables
        self.inputPath = ''
        self.outputPath = ''
        self.LogName='Point to Polygon'

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('PointToPolygon', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        # Create the dialog (after translation) and keep reference
        self.dlg = PointToPolygonDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        self.doInitGui()

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ':/plugins/PointToPolygon/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create squares around points'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Point to Polygon'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def cleanErrorMessage(self):
        self.dlg.labelErrorMessage.clear()

    def updateSBPaddingX(self):
        self.dlg.labelErrorMessage.clear()
        if self.dlg.radioSquare.isChecked() or self.dlg.radioHexagon.isChecked():
            self.dlg.spinBoxPaddingY.setValue(self.dlg.spinBoxPaddingX.value())

    def openInput(self):
        # reset labelPadding
        self.dlg.labelPadding.setText('Distance to centre (in input unit)')
        # file dialog
        dialog = QFileDialog()
        self.inShapefile = dialog.getOpenFileName(self.dlg,"Open vector file", self.inputPath)
        if self.inShapefile == '':
            return True
        self.cleanErrorMessage()
        # open file, guess driver
        self.inDataSource = ogr.Open(self.inShapefile, 0)
        if self.inDataSource is None:
            return False
        self.inLayer = self.inDataSource.GetLayer()
        self.spatialRef = self.inLayer.GetSpatialRef()
        # update interface
        if self.spatialRef.GetAttrValue('unit') is not None:
            self.dlg.labelPadding.setText('Distance to centre (in input unit: {})'.format(self.spatialRef.GetAttrValue('unit')))
        # change padding default increment according to type
        if self.spatialRef.GetAttrValue('unit').lower() in ['meters','meter']:
            self.dlg.spinBoxPaddingX.setSingleStep(1.0)
            self.dlg.spinBoxPaddingY.setSingleStep(1.0)
        else:
            self.dlg.spinBoxPaddingX.setSingleStep(0.1)
            self.dlg.spinBoxPaddingY.setSingleStep(0.1)

        # once all done, update text field
        self.dlg.textFileInput.setText(self.inShapefile)
        # and save path for next time
        self.inputPath =  os.path.dirname(self.inShapefile); 

        return True

    def addExtension(self, fname, ext):
        thisExt = os.path.splitext(fname)[-1]
        if thisExt != ext:
            return '{}{}'.format(fname, ext)
        else:
            return fname

    def selectOutput(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        thisFile = dialog.getSaveFileName(self.dlg, "Define an ESRI shapefile name", self.outputPath, filter='*.shp') #os.path.expanduser("~"))
        if thisFile=='':
            return True
        self.outShapefile = self.addExtension(thisFile, '.shp')
        self.cleanErrorMessage()

        # once all ok, update text
        self.dlg.textFileOutput.setText(self.outShapefile)

        self.outputPath = os.path.dirname(self.outShapefile)
        self.outputOk = True
        return True

    #
    # Creates and output, read the input, transform input features into centroids, for each centroid
    # creates a polygon around, save them to the output.
    # Input: from self values, defined by the interface
    #
    def doProcessing(self):
        # create output, copy projection from input
        try:
            outDriver = ogr.GetDriverByName("ESRI Shapefile")
            if os.path.exists(self.outShapefile):
                outDriver.DeleteDataSource(self.outShapefile)
        except:
            # error message to push
            iface.messageBar().pushMessage("Error", "Could not create output layer. Check this layer is not already open.", level=QgsMessageBar.CRITICAL)
            QgsMessageLog.logMessage("uld not create output layer. Check this layer is not already open.", self.LogName, QgsMessageLog.INFO)
            return False

        polygonType='square'
        if self.dlg.radioRectangle.isChecked():
            polygonType='rectangle'
        elif self.dlg.radioHexagon.isChecked():
            polygonType='hexagon'
        elif self.dlg.radioCentroid.isChecked():
            polygonType='centroid'

        self.outDS = outDriver.CreateDataSource(self.outShapefile)
        if polygonType=='centroid':
            self.outLayer = self.outDS.CreateLayer("point", self.spatialRef, geom_type=ogr.wkbPoint)
        else:
            self.outLayer = self.outDS.CreateLayer("polygon", self.spatialRef, geom_type=ogr.wkbPolygon)

        layerDefinition = self.inLayer.GetLayerDefn()
        for ii in range(layerDefinition.GetFieldCount()):
            fieldDefn = layerDefinition.GetFieldDefn(ii)
            self.outLayer.CreateField(fieldDefn)

        paddingX=self.dlg.spinBoxPaddingX.value()
        paddingY=self.dlg.spinBoxPaddingY.value()
        angle = math.radians(self.dlg.spinBoxAngle.value())

        for feature in self.inLayer:
            geom = feature.GetGeometryRef()
            # can take any input in, consider only the centroids.
            xx = geom.Centroid().GetX()
            yy = geom.Centroid().GetY()
 
            if polygonType=='centroid':
                thisPoint = ogr.Geometry(ogr.wkbPoint)
                thisPoint.AddPoint(xx, yy)
                outFeature = ogr.Feature(self.outLayer.GetLayerDefn())
                outFeature.SetGeometry(thisPoint)
            else:
                poly = ogr.Geometry(ogr.wkbPolygon)
                poly.AddGeometry( doPolygon(xx, yy, paddingX, paddingY, angle, polygonType) )
                outFeature = ogr.Feature(self.outLayer.GetLayerDefn())
                outFeature.SetGeometry(poly)
            # copy over all input fields to the output layer
            for ii in range(layerDefinition.GetFieldCount()):
                outFeature.SetField(layerDefinition.GetFieldDefn(ii).GetNameRef(), feature.GetField(ii))
            self.outLayer.CreateFeature(outFeature)

            outFeature = None

        # close files (force saving)
        self.inDataSource = None
        self.outDS = None

        return True

    def radioButton(self, polygonType):
        if polygonType == 'rectangle':
            self.dlg.spinBoxPaddingY.setEnabled(True)
            self.dlg.spinBoxPaddingX.setEnabled(True)
            self.dlg.spinBoxAngle.setEnabled(True)
        elif polygonType in ['square','hexagon']:
            self.dlg.spinBoxPaddingY.setEnabled(False)
            self.dlg.spinBoxPaddingX.setEnabled(True)
            self.dlg.spinBoxAngle.setEnabled(True)
        else: #centroid
            self.dlg.spinBoxPaddingY.setEnabled(False)
            self.dlg.spinBoxPaddingX.setEnabled(False)
            self.dlg.spinBoxAngle.setEnabled(False)

    def OpenInQGis(self):
        if self.dlg.radioCentroid.isChecked():
            outLayerName = "Centroid"
        else:
            outLayerName = "Padded"
        layer = self.iface.addVectorLayer(self.outShapefile, outLayerName, "ogr")
        if not layer:
            iface.messageBar().pushMessage("Error", "Layer failed to load", level=QgsMessageBar.CRITICAL)
            QgsMessageLog.logMessage("Layer failed to load", self.LogName, QgsMessageLog.INFO)

    def isOpen(self, file):
        listFile = [ layer.source() for layer in QgsMapLayerRegistry.instance().mapLayers().values()]
        if u'{}'.format(file) in listFile:
            return True
        return False

    def doCheckToGo(self):
        # first action is to force the input/output variables to the text written in the textEdit, in case the user changed them manually
        if self.dlg.textFileInput.toPlainText() != '':
            self.inShapefile = self.dlg.textFileInput.toPlainText()
        if self.dlg.textFileOutput.toPlainText() != '':
            self.outShapefile = self.dlg.textFileOutput.toPlainText()

        # Check input is defined and ok
        if self.inDataSource is None:
            self.dlg.labelErrorMessage.setText('Missing an input vector file')
            return False
        # check ouput is defined and ok
        if not self.outputOk:
            self.dlg.labelErrorMessage.setText('Please define an output shapefile')
            return False
        # if output already open return False
        if self.isOpen(self.outShapefile):
            self.dlg.labelErrorMessage.setText('Output file is alread open in QGis. Change output or close.')
            return False
        # check padding >0
        if not self.dlg.radioCentroid.isChecked():
            if self.dlg.spinBoxPaddingX.value() <= 0.0:
                self.dlg.labelErrorMessage.setText('Padding must be > 0.0')
                return False
            if self.dlg.radioRectangle.isChecked() and self.dlg.spinBoxPaddingY.value() <=0.0:
                self.dlg.labelErrorMessage.setText('Y padding must be > 0.0 for a rectangle')
        # all clear
        return True

    def doInitGui(self):
        # set the interface and signals
        self.dlg.buttonFileInput.clicked.connect(self.openInput)
        self.dlg.buttonFileOutput.clicked.connect(self.selectOutput)
        self.dlg.spinBoxPaddingX.valueChanged.connect(self.updateSBPaddingX)
        self.dlg.spinBoxPaddingY.valueChanged.connect(self.cleanErrorMessage)
        # radio button and their signals
        self.dlg.radioSquare.clicked.connect(lambda: self.radioButton('square'))
        self.dlg.radioRectangle.clicked.connect(lambda: self.radioButton('rectangle'))
        self.dlg.radioHexagon.clicked.connect(lambda: self.radioButton('hexagon'))
        self.dlg.radioCentroid.clicked.connect(lambda: self.radioButton('centroid'))
        # clean the interface
        self.resetGUI()

    # resetGUI to be called each time the plugin is ran
    def resetGUI(self):
        # boolean for checkToGo
        self.inDataSource = None
        self.outputOk = False
        # clean the interface
        self.dlg.textFileInput.clear()
        self.dlg.textFileOutput.clear()
        self.dlg.spinBoxPaddingX.setValue(0.0)
        self.dlg.spinBoxPaddingX.setSingleStep(0.1)
        self.dlg.spinBoxPaddingY.setValue(0.0)
        self.dlg.spinBoxPaddingY.setSingleStep(0.1)
        # set the radio buttons
        self.dlg.radioCentroid.setChecked(False)
        self.dlg.radioSquare.setChecked(True)
        self.dlg.spinBoxPaddingY.setEnabled(False)
        self.dlg.radioRectangle.setChecked(False)
        self.dlg.radioHexagon.setChecked(False)
        # the communication section
        self.dlg.labelErrorMessage.clear()

    def run(self):
        # clean the interface
        self.resetGUI()
        self.dlg.show()
        # Run the dialog event loop
        checkToGo = False
        while not checkToGo:
            runApp = self.dlg.exec_()
            # See if OK was pressed
            if runApp: # run=True, check if one can run
                checkToGo = self.doCheckToGo()
            else: # cancel=True
                checkToGo = True

        if runApp:
            if self.doProcessing():
                if self.dlg.checkBoxOpenQGis.checkState():
                    self.OpenInQGis()


