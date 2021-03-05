#!/usr/bin/env python3
#
# Copyright (c) 2014,2021 Darran Hunt (darran [at] hunt dot net dot nz)
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify  
# it under the terms of the GNU General Public License as published by  
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

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
parser.add_option('-t', '--ttf', help='ttf font file name', dest='ttf', default=None)
parser.add_option('-n', '--name', help='name for font', dest='name', default=None)
parser.add_option('-o', '--output', help='name of output file', dest='output', default=None)
parser.add_option('-d', '--depth', help='bits per pixel (default: 2)', type='int', dest='depth', default=2)
parser.add_option('-s', '--scale', help='scale font by this (default: 1.0)', type='float', dest='scale', default=1.0)
parser.add_option('-l', '--list', help='list glyphs', action='store_true', dest='list', default=False)
parser.add_option('-v', '--verbose', help='enable verbose output', action='count', dest='verbose', default=0)
(opts, args) = parser.parse_args()

if opts.ttf is None:
    parser.error('ttf opt is required')

if opts.output is None:
    opts.output = os.path.basename(opts.ttf)[:-4]

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

def writeHeader(outfd, fontName, height):
    print( '/*', file=outfd)
    print( ' * Font {}'.format(fontName), file=outfd)
    print( ' */', file=outfd)
    print( '', file=outfd)
    print( '#define {}_HEIGHT {}'.format(fontName.upper(),height), file=outfd)
    print( '', file=outfd)

def getMinWidth(ch, pixels,verbose=0):
    minWidth = 0
    mwidth = 0
    for line in pixels:
        if verbose:
            print('gmw: {}'.format(line))
        for xind in range(len(line)-2,0,-3):
            if line[xind] == 255:
                minWidth = xind+2
            else:
                break
        if verbose:
            print('gmw: {} -> {}'.format(len(line), minWidth))
        if minWidth > mwidth:
            mwidth = minWidth

    if verbose:
        print('gmw: -> {}'.format(mwidth))
    return mwidth

def getGlyphMap(fontName, chars, glyphData, glyphd):
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

    return glyphHeaderStr,chMap

def writeAsciiMap(outfd, fontName, chMap):
    print( '\n/* Mapping from ASCII codes to font characters, from space (0x20) to del (0x7f) */', file=outfd)
    print( 'const uint8_t {}_asciimap[{}] __attribute__((__progmem__)) = {{ '.format(fontName,len(chMap)), end='', file=outfd)
    glyphMap = []
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
    return glyphMap


def writeGlyphs(outfd, fontName, chars):
    glyphd = {}
    glyphData = {}
    header = True
    for ch in chars:
        glyphName = getGlyphName(ch)
        pngFilename = 'output/{}.png'.format(glyphName)
        glyph = png.Reader(pngFilename)
        width, height, pixels, meta = glyph.asDirect()
        glyphd[glyphName] = dict(width=width, height=height, meta=meta)
        maxWidth = width
        if opts.verbose > 2:
            print(meta)
        if opts.verbose > 1:
            print('{}: width: {}, height: {}'.format(ch, width,height))

        if header:
            writeHeader(outfd, fontName, height)
            header = False

        yoff = 0
        yind = 0
        pind = 'r'
        line = {}
        pixs = list(pixels)
        minWidth = getMinWidth(ch, list(pixs))
        if opts.verbose > 1:
            print('{}: width {} minWidth {}'.format(ch, width, minWidth))

        #width, height, pixels, meta = glyph.asDirect()
        for item in pixs:
            if opts.verbose > 2:
                print('{}: {}'.format(yind,item))
            if isBlankLine(item):
                yoff += 1
                continue
            line[yind] = []
            for xind in range(0,minWidth,3):
                line[yind].append(dict(r=item[xind+0], g=item[xind+1], b=item[xind+2]))
                #line[yind].append(dict(r=item[xind+0], g=item[xind+1], b=item[xind+2], a=255-item[xind+3]))
            if opts.verbose > 2:
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

    return count, glyphd, glyphData

def generateGlyphHeader(fontName, chars):
    print("Writing {} glyphs to {}.h".format(len(chars),opts.output))

    outfd = open('{}.h'.format(opts.output), 'w')
    print('#ifndef {}_H_'.format(fontName.upper()), file=outfd)
    print('#define {}_H_'.format(fontName.upper()), file=outfd)

    count, glyphd, glyphData = writeGlyphs(outfd, fontName, chars)
    glyphHeaderStr,chMap = getGlyphMap(fontName, chars, glyphData, glyphd)
    glyphMap = writeAsciiMap(outfd, fontName, chMap)

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

    cm = font['cmap']
    t = cm.getcmap(3,1).cmap
    s = font.getGlyphSet()
    units_per_em = font['head'].unitsPerEm
    width = s[t[ord('0')]].width
    # get max width
    maxWidth = 0
    for ch in chars:
        glyphName =  getGlyphName(ch)
        width = s[t[ord(ch)]].width
        if opts.verbose > 1:
            print(ch)
            print('{}: Width in points: {}'.format(glyphName, width))
        if width > maxWidth:
            maxWidth = width
            maxCh = ch
            maxGlyphName = glyphName

    maxCm = maxWidth*2.54/72
    gscale = (0.5 / maxCm) * opts.scale
    if opts.verbose:
        print('{}: max Width in points: {}'.format(maxGlyphName, maxWidth))
        print('Width in inches: %f' % (maxWidth/72))
        print('Width in cm: %f' % (maxCm))
        print('gscale {}'.format(gscale))
        print('scaled max Width in points: {}'.format(maxGlyphName, maxWidth*gscale))
        print('scaled Width in inches: %f' % (maxWidth/72*gscale))
        print('scaled Width in cm: %f' % (maxCm*gscale))

    ref = gs['zero']
    baseWidth = ref.width
    for ch in chars:
        glyphName =  getGlyphName(ch)
        pen = ReportLabPen(gs, Path(fillColor=colors.black, strokeWidth=1))
        g = gs[glyphName]
        g.draw(pen)
        if opts.verbose > 1:
            print('{}: width: {}, height: {}'.format( ch, g.width, g.height))

        w = int((g.width / float(ref.width)) * 30.9) * opts.scale
        h = 28 * opts.scale
        if opts.verbose > 1:
            print('{}: width: {}, height: {}, w: {}, h: {}'.format( ch, g.width, g.height, w, h))
        #gscale = float(31.0 / float(g.width)) * 0.45
        from reportlab.graphics import renderPM
        from reportlab.graphics.shapes import Group, Drawing, scale

        # Everything is wrapped in a group to allow transformations.
        g = Group(pen.path)
        #g.translate(0, 180)
        #g.scale(0.008, 0.008)
        g.scale(gscale, gscale)

        d = Drawing(w, h)
        d.add(g)

        imageFile = "output/%s.png" % glyphName
        renderPM.drawToFile(d, imageFile, fmt="PNG")

def main():
    #chars = 'abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ%$'
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
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
