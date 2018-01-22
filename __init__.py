# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PointToPolygon
                                 A QGIS plugin
 Creates polygons around points
                             -------------------
        begin                : 2018-01-19
        copyright            : (C) 2018 by Bruno Combal
        email                : bruno.combal@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load PointToPolygon class from file PointToPolygon.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .pointtopolygon import PointToPolygon
    return PointToPolygon(iface)
