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

#
# returns a polygon ring around a central point
# inputs:
#   xx, yy: central point coordinates
#   paddingX, paddingY: padding around the centroid, defines the output ring size.
#   angle: rotation angle (radians) to apply to the output polygon
#   polygonType: type of polygon, defines the output polygons vertex coordinates
#
from osgeo import ogr
import math

polygonTypes = ['point','square','rectangle','hexagon']
sqrt3_2 = 0.5*math.sqrt(3)

def doPolygon(xx, yy, paddingX, paddingY, angle, polygonType):

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
        pointList.append([xx + 0.5*paddingX, yy + sqrt3_2*paddingX])
        pointList.append([xx + paddingX, yy])
        pointList.append([xx + 0.5*paddingX, yy - sqrt3_2*paddingX])
        pointList.append([xx - 0.5*paddingX, yy - sqrt3_2*paddingX])
        pointList.append([xx - paddingX, yy])
        pointList.append([xx - 0.5*paddingX, yy + sqrt3_2*paddingX])
        pointList.append([xx + 0.5*paddingX, yy + sqrt3_2*paddingX])

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

