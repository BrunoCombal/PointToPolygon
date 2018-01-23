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

class PointToPolygon:
    """QGIS Plugin Implementation."""

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

        # application variables
        self.inputPath = ''
        self.outputPath = ''
        self.sqrt3_2 = 0.5*math.sqrt(3)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
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
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

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

    def openInput(self):
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

        # once all done, update text field
        self.dlg.textFileInput.setText(self.inShapefile)
        # and save path for next time
        self.inputPath =  os.path.dirname(self.inShapefile); 

        return True

    def addExtension(self, fname, ext):
        print 'add extension'
        thisExt = os.path.splitext(fname)[-1]
        print fname, thisExt
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

    def doPolygon(self, xx, yy, paddingX, paddingY, angle, polygonType):

        pointList=[]

        if polygonType == 'square':
            pointList.append([xx-paddingX, yy+paddingX])
            pointList.append([xx+paddingX, yy+paddingX])
            pointList.append([xx+paddingX, yy-paddingX])
            pointList.append([xx-paddingX, yy-paddingX])
            pointList.append([xx-paddingX, yy+paddingX])
        elif polygonType == 'rectangle':
            pointList.append([xx-paddingX, yy+paddingY])
            pointList.append([xx+paddingX, yy+paddingY])
            pointList.append([xx+paddingX, yy-paddingY])
            pointList.append([xx-paddingX, yy-paddingY])
            pointList.append([xx-paddingX, yy+paddingY])
        elif polygonType == 'hexagon':
            pointList.append([xx + 0.5*paddingX, yy + self.sqrt3_2*paddingX])
            pointList.append([xx + paddingX, yy])
            pointList.append([xx + 0.5*paddingX, yy - self.sqrt3_2*paddingX])
            pointList.append([xx - 0.5*paddingX, yy - self.sqrt3_2*paddingX])
            pointList.append([xx- paddingX, yy])
            pointList.append([xx-0.5*paddingX, yy + self.sqrt3_2*paddingX])
            pointList.append([xx + 0.5*paddingX, yy + self.sqrt3_2*paddingX])

        if angle !=0:
            tmp = []
            cosa = math.cos(angle)
            sina = math.sin(angle)
            for ii in pointList:
                xrot = (ii[0]-xx) * cosa - (ii[1]-yy) * sina  
                yrot = (ii[0]-xx) * sina + (ii[1]-yy) * cosa
                tmp.append([xrot + xx, yrot + yy])
            pointList = None
            pointList = tmp

        ring = ogr.Geometry(ogr.wkbLinearRing)
        for iPoint in pointList:
            ring.AddPoint(iPoint[0], iPoint[1])


        return ring

    def doProcessing(self):
        # create output, copy projection from input
        outDriver = ogr.GetDriverByName("ESRI Shapefile")
        if os.path.exists(self.outShapefile):
            try:
                outDriver.DeleteDataSource(self.outShapefile)
            except:
                # error message to push
                return False
                pass

        self.outDS = outDriver.CreateDataSource(self.outShapefile)
        self.outLayer = self.outDS.CreateLayer("polygon", self.spatialRef, geom_type=ogr.wkbPolygon)
        # copy all fields from points to polygons
        # list of fields
        layerDefinition = self.inLayer.GetLayerDefn()
        for ii in range(layerDefinition.GetFieldCount()):
            fieldDefn = layerDefinition.GetFieldDefn(ii)
            self.outLayer.CreateField(fieldDefn)

        paddingX=self.dlg.spinboxPadding.value()
        paddingY=self.dlg.spinBoxPaddingY.value()
        angle = math.radians(self.dlg.spinBoxAngle.value())
        polygonType='square'
        if self.dlg.radioRectangle.isChecked():
            polygonType='rectangle'
        elif self.dlg.radioHexagon.isChecked():
            polygonType='hexagon'

        for feature in self.inLayer:
            geom = feature.GetGeometryRef()
            # can take any input in, consider only the centroids.
            xx = geom.Centroid().GetX()
            yy = geom.Centroid().GetY()
 
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry( self.doPolygon(xx, yy, paddingX, paddingY, angle, polygonType) )
            outFeature = ogr.Feature(self.outLayer.GetLayerDefn())
            outFeature.SetGeometry(poly)
            self.outLayer.CreateFeature(outFeature)
            for ii in range(layerDefinition.GetFieldCount()):
                outFeature.SetField(layerDefinition.GetFieldDefn(ii).GetNameRef(), feature.GetField(ii))

            outFeature = None

        # close files (force saving)
        self.inDataSource = None
        self.outDS = None

        return True

    def radioButton(self, polygonType):
        if polygonType == 'rectangle':
            self.dlg.spinBoxPaddingY.setEnabled(True)
        else:
            self.dlg.spinBoxPaddingY.setEnabled(False)

    def OpenInQGis(self):
        layer = self.iface.addVectorLayer(self.outShapefile, "Padded", "ogr")
        if not layer:
            print "Layer failed to load!"

    def doCheckToGo(self):
        # Check input is defined and ok
        if self.inDataSource is None:
            self.dlg.labelErrorMessage.setText('Missing an input vector file')
            return False
        # check ouput is defined and ok
        if not self.outputOk:
            self.dlg.labelErrorMessage.setText('Please define an output shapefile')
            return False
        # check padding >0
        if self.dlg.spinboxPadding.value() <= 0.0:
            self.dlg.labelErrorMessage.setText('Padding must be > 0.0')
            return False
        if self.dlg.radioRectangle.isChecked() and self.dlg.spinBoxPaddingY.value() <=0.0:
            self.dlg.labelErrorMessage.setText('Y padding must be > 0.0 for a rectangle')
        # all clear
        return True

    def doInitGui(self):
        # boolean for checkToGo
        self.inDataSource = None
        self.outputOk = False

        self.dlg.textFileInput.clear()
        self.dlg.textFileOutput.clear()
        self.dlg.buttonFileInput.clicked.connect(self.openInput)
        self.dlg.buttonFileOutput.clicked.connect(self.selectOutput)
        self.dlg.spinboxPadding.setValue(0.0)
        self.dlg.spinboxPadding.valueChanged.connect(self.cleanErrorMessage)
        self.dlg.spinBoxPaddingY.valueChanged.connect(self.cleanErrorMessage)

        self.dlg.radioSquare.clicked.connect(lambda: self.radioButton('square'))
        self.dlg.radioSquare.setChecked(True)
        self.dlg.spinBoxPaddingY.setEnabled(False)
        self.dlg.radioRectangle.clicked.connect(lambda: self.radioButton('rectangle'))
        self.dlg.radioRectangle.setChecked(False)
        self.dlg.radioHexagon.clicked.connect(lambda: self.radioButton('hexagon'))
        self.dlg.radioHexagon.setChecked(False)

        self.dlg.labelErrorMessage.clear()
        return True

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.doInitGui()
        self.dlg.show()
        # Run the dialog event loop
        checkToGo = False
        while not checkToGo:
            runApp = self.dlg.exec_()
            # See if OK was pressed
            if runApp: # run=True, check if one can run
                print 'runApp ok'
                checkToGo = self.doCheckToGo()
                print 'checkToGo ',checkToGo
            else: # cancel=True
                checkToGo = True

        if runApp:
            print 'running doProcessing'
            if self.doProcessing():
                if self.dlg.checkBoxOpenQGis.checkState():
                    self.OpenInQGis()
