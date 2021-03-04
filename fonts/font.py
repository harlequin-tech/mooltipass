#!/usr/bin/env python3
#
# Copyright (c) 2014 Darran Hunt (darran [at] hunt dot net dot nz)
# All rights reserved.
#
# CDDL HEADER START
#
# The contents of this file are subject to the terms of the
# Common Development and Distribution License (the "License").
# You may not use this file except in compliance with the License.
#
# You can obtain a copy of the license at src/license_cddl-1.0.txt
# or http://www.opensolaris.org/os/licensing.
# See the License for the specific language governing permissions
# and limitations under the License.
#
# When distributing Covered Code, include this CDDL HEADER in each
# file and include the License file at src/license_cddl-1.0.txt
# If applicable, add the following below this CDDL HEADER, with the
# fields enclosed by brackets "[]" replaced with your own identifying
# information: Portions Copyright [yyyy] [name of copyright owner]
#
# CDDL HEADER END
#/

import sys,os
import png, math
import xml.etree.ElementTree as ET
import numpy as np
from optparse import OptionParser
from struct import *

from fontTools.misc.py23 import *
from fontTools.pens.basePen import BasePen
from reportlab.graphics.shapes import Path
from fontTools.ttLib import TTFont
from reportlab.lib import colors




parser = OptionParser(usage = 'usage: %prog [opts]')
parser.add_option('-f', '--font', help='font file', dest='font', default=None)
parser.add_option('-n', '--name', help='name for font', dest='name', default=None)
parser.add_option('-t', '--ttf', help='ttf font file name', dest='ttf', default=None)
parser.add_option('-p', '--png', help='png file for font', dest='png', default=None)
parser.add_option('-x', '--xml', help='xml file for font', dest='xml', default=None)
parser.add_option('-o', '--output', help='name of output file', dest='output', default='font')
parser.add_option('-d', '--depth', help='bits per pixel (default: 2)', type='int', dest='depth', default=2)
parser.add_option('-l', '--list', help='list glyphs', action='store_true', dest='list', default=False)
parser.add_option('', '--debug', help='enable debug output', action='store_true', dest='debug', default=False)
parser.add_option('', '--verbose', help='enable verbose output', action='store_true', dest='verbose', default=False)
(opts, args) = parser.parse_args()

CHAR_EURO = 0x20ac      # Euro currency sign, not yet supported

#if opts.ttf is None or (opts.name == None or opts.png == None or opts.xml == None):
#    parser.error('name, png, and xml opts are required')

extendedChars = {
    0xB0: 'Degree Sign',
    0xE0: '`a - Latin Small Letter A with Grave',
    0xE1: '\'a - Latin Small Letter A with Acute',
    0xE2: '^a - Latin Small Letter A with Circumflex',
    0xE3: '~a - Latin Small Letter A with Tilde',
    0xE4: '"a - Latin Small Letter A with Diaeresis',
    0xE5: ' a - Latin Small Letter A with Ring Above',
    0xE6: 'ae - Latin Small Letter Ae',
    0xE7: ' c - Latin Small Letter c with Cedilla',
    0xE8: '`e - Latin Small Letter E with Grave',
    0xE9: '\'e - Latin Small Letter E with Acute',
    0xEA: '^e - Latin Small Letter E with Circumflex',
    0xEB: '"e - Latin Small Letter E with Diaeresis',
    0x20AC: ' E - Euro Sign'
}

cmap = {'0': 'zero', 
        '1': 'one', 
        '2': 'two', 
        '3': 'three', 
        '4': 'four', 
        '5': 'five', 
        '6': 'six', 
        '7': 'seven', 
        '8': 'eight', 
        '9': 'nine',
        '%': 'percent',
        '!': 'exclam',
        '$': 'dollar',
        }

def getGlyphName(ch):
    if ch in cmap:
        return cmap[ch]
    else:
        return ch

#__all__ = ["ReportLabPen"]

class ReportLabPen(BasePen):

    """A pen for drawing onto a reportlab.graphics.shapes.Path object."""

    def __init__(self, glyphSet, path=None):
        BasePen.__init__(self, glyphSet)
        if path is None:
            path = Path()
        self.path = path

    def _moveTo(self, p):
        (x,y) = p
        self.path.moveTo(x,y)

    def _lineTo(self, p):
        (x,y) = p
        self.path.lineTo(x,y)

    def _curveToOne(self, p1, p2, p3):
        (x1,y1) = p1
        (x2,y2) = p2
        (x3,y3) = p3
        self.path.curveTo(x1, y1, x2, y2, x3, y3)

    def _closePath(self):
        self.path.closePath()

def isBlankLine(line):
    for data in line:
        if data != 255:
            return False
    return True

def generateGlyphHeader(fontName, chars):
    header = True
    outfd = open('{}.h'.format(opts.output), 'w')
    print('#ifndef {}_H_'.format(fontName.upper()), file=outfd)
    print('#define {}_H_'.format(fontName.upper()), file=outfd)
    glyphd = {}
    glyphData = {}
    for ch in chars:
        glyphName = getGlyphName(ch)
        pngFilename = 'output/{}.png'.format(glyphName)
        glyph = png.Reader(pngFilename)
        width, height, pixels, meta = glyph.asDirect()
        glyphd[glyphName] = dict(width=width, height=height, meta=meta)
        maxWidth = width
        if opts.verbose:
            print(meta)
            print('{}: width: {}, height: {}'.format(ch, width,height))
        if header:
            print( '/*', file=outfd)
            print( ' * Font {}'.format(fontName), file=outfd)
            print( ' */', file=outfd)
            print( '', file=outfd)
            print( '#define {}_HEIGHT {}'.format(fontName.upper(),height), file=outfd)
            print( '', file=outfd)
            header = False


        yoff = 0
        yind = 0
        pind = 'r'
        line = {}
        while True:
            try:
                item = pixels.__next__()
            except:
                break
            if opts.verbose:
                print('{}: {}'.format(yind,item))
            if isBlankLine(item):
                yoff += 1
                continue
            line[yind] = []
            for xind in range(0,len(item),3):
                line[yind].append(dict(r=item[xind+0], g=item[xind+1], b=item[xind+2]))
                #line[yind].append(dict(r=item[xind+0], g=item[xind+1], b=item[xind+2], a=255-item[xind+3]))
            if opts.verbose:
                print('{}: {}'.format(yind,line[yind]))
            yind += 1

        asciiPixel = [' ', '.', '*', '*',
                      '*', '*', '*', '*',
                      '*', '*', '*', '*',
                      '*', '*', '*', '*']

        count = 0
        glyphData[glyphName] = []
        glyphd[glyphName]['yoff'] = yoff
        offset = 0
        print( "const uint8_t {}_{:#x}[] __attribute__((__progmem__)) = {{   /* '{}' width: {} */".format(fontName,ord(ch), ch, width), file=outfd)

        x = 0
        for y in range(0,height-yoff):
            patt = ''
            print( '    ', end='', file=outfd)
            lineWidth = 1
            pixels = 0
            pixCount = 0
            for pixel in line[y]:
                count += 1
                # map 255 shades to 4
                pix = (255-pixel[pind]) >> (8-opts.depth)
                pixels = pixels << opts.depth | pix
                pixCount += 1
                if pixCount >= (8/opts.depth):
                    lineWidth += 1
                    print( '0x{:02x}, '.format(pixels), end='', file=outfd)
                    glyphData[glyphName].append(pixels & 0xFF)
                    pixels = 0
                    pixCount = 0

                patt += asciiPixel[pix]

            glyphData[glyphName].append(pixels & 0xFF)
            if lineWidth < (maxWidth+3)/4:
                for ind in range(lineWidth, int((maxWidth+3)/4)):
                    print( '      ', end='', file=outfd)
            print(' /* [{}] */'.format(patt), file=outfd)
        print('};\n', file=outfd)
        print('', file=outfd)

    # map
    index = 0
    chMap = []
    glyphHeader = {}
    glyphOffset = 0
    glyphHeaderStr = ''
    for ch in range(ord(' '), 255):
        glyphName = getGlyphName(chr(ch))
        if chr(ch) in chars and glyphName in glyphData:
            chMap.append(index)
            index += 1
            glyph = glyphd[glyphName]
            rect = [0,0,glyph['height'],glyph['width']]
            offset = [0,glyph['yoff']]
            if ch == ord(' '):
                glyphHeaderStr += "    {{ {:>2}, {:>2}, {:>2}, {:>2}, {:>2}, -1 }}, /* '{}' */\n".format(glyph['width'], 
                    rect[2], rect[3], offset[0], offset[1], glyph['code'])
                glyphHeader[ch] = pack('=BBBbbH', int(glyph['width']), rect[2], rect[3], offset[0], offset[1], 0xFFFF)
            else:
                if ch > 127:
                    if extendedChars.has_key(ch):
                        char = extendedChars[ch]
                    else:
                        char = '~'
                else:
                    char = chr(ch)
                glyphHeaderStr += "    {{ {:>2}, {:>2}, {:>2}, {:>2}, {:>2}, {}_{:#x} }}, /* '{}' */\n".format(glyph['width'], 
                    rect[2], rect[3], offset[0], offset[1], fontName, ch, char)
                glyphHeader[ch] = pack('=BBBbbH', int(glyph['width']), rect[2], rect[3], offset[0], offset[1], glyphOffset)
                glyphOffset += len(glyphData[glyphName])
        else:
            chMap.append(None)

    glyphMap = []

    print( '\n/* Mapping from ASCII codes to font characters, from space (0x20) to del (0x7f) */', file=outfd)
    print( 'const uint8_t {}_asciimap[{}] __attribute__((__progmem__)) = {{ '.format(fontName,len(chMap)), end='', file=outfd)
    index = 0
    for item in chMap:
        if index == 0:
            print('\n    ', end='', file=outfd)
            index = 16
        if item != None:
            glyphMap.append(item)
            print( '{:>3}, '.format(item), end='', file=outfd)
        else:
            glyphMap.append(255)
            print( '255, ', end='', file=outfd)
        index -= 1
    print('\n};', file=outfd)

    if len(chMap) < 256:
        glyphMap.extend([255 for i in range(0, 256-len(chMap))])


    # glyph_t
    print('\nconst glyph_t {}[] __attribute__((__progmem__)) = {{'.format(fontName), file=outfd)
    print(glyphHeaderStr, file=outfd, end='')
    print('};\n', file=outfd)

    print('#endif // {}_H_'.format(fontName.upper()), file=outfd)
    outfd.close()
    return count

def genpng(chars):

    font = TTFont(opts.ttf) 
    gs = font.getGlyphSet()
    a = gs['W']
    baseWidth = a.width
    for ch in chars:
        if ch in cmap:
            glyphName = cmap[ch]
        else:
            glyphName = ch
        pen = ReportLabPen(gs, Path(fillColor=colors.black, strokeWidth=1))
        g = gs[glyphName]
        g.draw(pen)
        if opts.verbose:
            print('{}: width: {}, height: {}'.format( ch, g.width, g.height))

        #w, h = g.width, 21
        w = int((g.width / float(a.width)) * 30.9)
        h = 28 
        if opts.verbose:
            print('{}: width: {}, height: {}, w: {}, h: {}'.format( ch, g.width, g.height, w, h))
        gscale = float(21.0 / float(g.width))
        from reportlab.graphics import renderPM
        from reportlab.graphics.shapes import Group, Drawing, scale

        # Everything is wrapped in a group to allow transformations.
        g = Group(pen.path)
        #g.translate(0, 180)
        g.scale(0.008, 0.008)
        #g.scale(gscale, gscale)

        d = Drawing(w, h)
        d.add(g)

        imageFile = "output/%s.png" % glyphName
        renderPM.drawToFile(d, imageFile, fmt="PNG")

def main():
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ%$'
    if opts.ttf:
        genpng(chars)
        if opts.name is None:
            opts.name = os.path.basename(opts.ttf)[:-4]
        generateGlyphHeader(opts.name, chars)
        return
        if opts.list:
            for name in glyphs:
                filename = 'output/' + name + ".png"
                print( '0x{:x}: {:17} -> {}'.format(glyphs[name].originalgid, name, filename))
            return
        for name in chars:
            if name in cmap:
                ind = cmap[name]
            else:
                ind = name
            if ind in glyphs:
                filename = 'output/' + ind + ".png"
                print( '0x{:x}: {:17} -> {}'.format(glyphs[ind].originalgid, name, filename))
                #glyphs[ind].export(filename, 20, 6)
                #glyphs[ind].export(filename, 20, 6)
                generateGlyphHeader('test', name, filename)
                return
        return

    generateHeader(opts.name, opts.png, opts.xml)

if __name__ == "__main__":
    main()
