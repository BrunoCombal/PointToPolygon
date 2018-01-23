#Point To Polygon#

A QGis plugin to transform a vector file of points into polygons (squares, rectangles or polygons) centered on those points.

The polygons dimension is defined by the padding parameters (for a square, the width is two times the padding value).
If the input file is a vector file of lines or polygons, the centroid of the features will be used to center the polygons.
The output polygons can be rotated, by changing the rotation angle, 0 means no rotation is applied.