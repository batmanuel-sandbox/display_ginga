#
# LSST Data Management System
# Copyright 2008, 2009, 2010, 2015 LSST Corporation.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#

##
## \file
## \brief Definitions to talk to ginga from python

from __future__ import absolute_import, division, print_function

import math
import os
import re
import sys
import time

from ginga.web.pgw import ipg

import lsst.afw.display.interface as interface
import lsst.afw.display.virtualDevice as virtualDevice
import lsst.afw.display.ds9Regions as ds9Regions

import lsst.afw.geom as afwGeom

try:
    _maskTransparency
except NameError:
    _maskTransparency = None

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def gingaVersion():
    """Return the version of ginga in use, as a string"""

    from ginga.version import version

    return version

if False:
    try:
        server
    except NameError:
        server = None

def initGinga(host='localhost', port=9914, use_opencv=False, no_ioloop=True):
    """
    Initialize ginga
    
    set use_opencv to True if you have a non-buggy python OpenCv bindings--it greatly speeds up some operations
    IMPORTANT: if running in an IPython/Jupyter notebook, use no_ioloop=True
    """
    
    global server
    if not server:
        server = ipg.make_server(host=host, port=port, use_opencv=use_opencv)
        server.start(no_ioloop=no_ioloop)

class GingaEvent(interface.Event):
    """An event generated by a mouse or key click on the display"""
    def __init__(self, k, x, y):
        interface.Event.__init__(self, k, x, y)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

class DisplayImpl(virtualDevice.DisplayImpl):
    server = None

    def __init__(self, display, verbose=False, open=False,
                 host='localhost', port=9914, use_opencv=False, no_ioloop=True,
                 canvas_format='jpeg',
                 *args, **kwargs):
        """
        Initialise a ginga display

        canvas_type  file type for displays ('jpeg': fast; 'png' : better, slow)
        """
        if not DisplayImpl.server:
            DisplayImpl.server = ipg.make_server(host=host, port=port, use_opencv=use_opencv)
            DisplayImpl.server.start(no_ioloop=no_ioloop)

        virtualDevice.DisplayImpl.__init__(self, DisplayImpl.server.get_viewer(str(display.frame)),
                                           verbose=False)
        self._canvas = self.display.add_canvas()
        #self.display.configure_surface(100, 100) # so show() won't fail

        # JPEG is faster, PNG looks better
        canvas_types = ('jpeg', 'png',)
        if canvas_format in canvas_types:
            settings = self.display.get_settings()
            settings.set(html5_canvas_format=canvas_format)
        else:
            print("Unknown format \"%s\" (allowed: \"%s\")" % (canvas_format, '", "'.join(canvas_types)))
        #
        # This may not be necessary, but the worst case is that the user has to close a tab
        #
        # N.b. the user may well want to call Display.embed() (a ginga specific call)
        #
        if open:
            self.display.open()
    #
    # Extensions to the API
    #
    def get_viewer(self):
        """Return the ginga viewer
        """
        return self.display

    def shutdown_server(self):
        """Shutdown the ginga server
        """
        if DisplayImpl.server:
            DisplayImpl.server.stop()
            DisplayImpl.server = None

    def show_color_bar(show=True):
        """Show (or hide) the colour bar"""
        self.display.show_color_bar(show)

    def show_pan_mark(show=True, color='red'):
        """Show (or hide) the colour bar"""
        self.display.show_pan_mark(show, color)

    def _close(self):
        """Called when the device is closed"""
        pass

    def _setMaskTransparency(self, transparency, maskplane):
        """Specify mask transparency (percent); or None to not set it when loading masks"""
        if maskplane != None:
            print("ginga is unable to set transparency for individual maskplanes" % maskplane,
                  file=sys.stderr)
            return

    def _getMaskTransparency(self, maskplane):
        """Return the current mask transparency"""

    def _mtv(self, image, mask=None, wcs=None, title=""):
        """Display an Image and/or Mask on a ginga display
        """

        self._erase()

        if image:
            # We'd call
            #   self.display.load_data(image.getArray())
            # except that we want to include the wcs
            #
            # Still need to handle the title
            #
            from ginga import AstroImage

            astroImage = AstroImage.AstroImage(logger=self.display.logger,
                                               data_np=image.getArray())
            if wcs is not None:
                astroImage.set_wcs(WcsAdaptorForGinga(wcs))

            self.display.set_image(astroImage)

        if mask:
            print("Mask displays are not yet supported in Ginga")
    #
    # Graphics commands
    #
    def _buffer(self, enable=True):
        pass

    def _flush(self):
        pass

    def _erase(self):
        """Erase the display"""
        self._canvas.delete_all_objects()

    def _dot(self, symb, c, r, size, ctype, fontFamily="helvetica", textAngle=None):
        """Draw a symbol at (col,row) = (c,r) [0-based coordinates]
    Possible values are:
            +                Draw a +
            x                Draw an x
            *                Draw a *
            o                Draw a circle
            @:Mxx,Mxy,Myy    Draw an ellipse with moments (Mxx, Mxy, Myy) (argument size is ignored)
            An object derived from afwGeom.ellipses.BaseCore Draw the ellipse (argument size is ignored)
    Any other value is interpreted as a string to be drawn. Strings obey the fontFamily (which may be extended
    with other characteristics, e.g. "times bold italic".  Text will be drawn rotated by textAngle (textAngle is
    ignored otherwise).

    N.b. objects derived from BaseCore include Axes and Quadrupole.
    """
        if isinstance(symb, afwGeom.ellipses.BaseCore):
            Ellipse = self._canvas.get_draw_class('ellipse')

            self._canvas.add(Ellipse(c, r, xradius=symb.getA(), yradius=symb.getB(),
                                     rot_deg=math.degrees(symb.getTheta()), color=ctype))
        elif symb == 'o':
            Circle = self._canvas.get_draw_class('circle')
            self._canvas.add(Circle(c, r, radius=size, color=ctype))
        else:
            Line = self._canvas.get_draw_class('line')
            Text = self._canvas.get_draw_class('text')

            for ds9Cmd in ds9Regions.dot(symb, c, r, size, fontFamily="helvetica", textAngle=None):
                tmp = ds9Cmd.split('#')
                cmd = tmp.pop(0).split()
                comment = tmp.pop(0) if tmp else ""

                cmd, args = cmd[0], cmd[1:]
                if cmd == "line":
                    self._canvas.add(Line(*[float(p) - 1 for p in args], color=ctype))
                elif cmd == "text":
                    x, y = [float(p) - 1 for p in args[0:2]]
                    self._canvas.add(Text(x, y, symb, color=ctype))
                else:
                    raise RuntimeError(ds9Cmd)

    def _drawLines(self, points, ctype):
        """Connect the points, a list of (col,row)
        Ctype is the name of a colour (e.g. 'red')"""

        Line = self._canvas.get_draw_class('line')
        p0 = points[0]
        for p in points[1:]:
            self._canvas.add(Line(p0[0], p0[1], p[0], p[1], color=ctype))
            p0 = p
    #
    # Set gray scale
    #
    def _scale(self, algorithm, min, max, unit, *args, **kwargs):
        self.display.set_color_map('gray')
        self.display.set_color_algorithm(algorithm)

        if min == "zscale":
            self.display.set_autocut_params('zscale', contrast=0.25)
            self.display.auto_levels()
        elif min == "minmax":
            self.display.set_autocut_params('minmax')
            self.display.auto_levels()
        else:
            if unit:
                print("ginga: ignoring scale unit %s" % unit)

            self.display.cut_levels(min, max)
    #
    # Zoom and Pan
    #
    def _zoom(self, zoomfac):
        """Zoom by specified amount"""

        self.display.scale_to(zoomfac, zoomfac)

    def _pan(self, colc, rowc):
        """Pan to (colc, rowc)"""

        self.display.set_pan(colc, rowc)

    def XXX_getEvent(self):
        """Listen for a key press, returning (key, x, y)"""

        raise RuntimeError("Write me")
    
        k = '?'
        x, y = self.display.get_pan()        

        return GingaEvent(k, x, y)

#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

class WcsAdaptorForGinga(object):
    """A class to adapt the LSST Wcs class for Ginga"""
    def __init__(self, wcs):
        self._wcs = wcs

    def pixtoradec(self, idxs, coords='data'):
        """Return (ra, dec) in degrees given a position in pixels"""
        ra, dec = self._wcs.pixelToSky(*idxs)

        return ra.asDegrees(), dec.asDegrees()

    def pixtosystem(self, idxs, system=None, coords='data'):
        """I'm not sure if ginga really needs this; equivalent to self.pixtoradec()"""
        return self.pixtoradec(idxs, coords=coords)

    def radectopix(self, ra_deg, dec_deg, coords='data', naxispath=None):
        """Return (x, y) in pixels given (ra, dec) in degrees"""

        return wcs.skyToPixel(ra_deg*afwGeom.degrees, dec_deg*afwGeom.degrees)
