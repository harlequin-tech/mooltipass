#!/usr/bin/env python
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

import sys
import png, math
import xml.etree.ElementTree as ET
import numpy as np
from optparse import OptionParser
from struct import *
import fontforge

parser = OptionParser(usage = 'usage: %prog [opts]')
parser.add_option('-n', '--name', help='name for font', dest='name', default=None)
parser.add_option('-t', '--ttf', help='ttf font file name', dest='ttf', default=None)
parser.add_option('-p', '--png', help='png file for font', dest='png', default=None)
parser.add_option('-x', '--xml', help='xml file for font', dest='xml', default=None)
parser.add_option('-o', '--output', help='name of output file', dest='output', default='font')
parser.add_option('-d', '--depth', help='bits per pixel (default: 2)', type='int', dest='depth', default=2)
parser.add_option('-l', '--list', help='list glyphs', action='store_true', dest='list', default=False)
parser.add_option('', '--debug', help='enable debug output', action='store_true', dest='debug', default=False)
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

def generateGlyphHeader(fontName, ch, pngFilename):
    print('testing {}'.format(ch))
    glyph = png.Reader(pngFilename)
    width, height, pixels, meta = glyph.asDirect()
    print('width: {}, height: {}'.format(width,height))
    print(dir(pixels))
    print(meta)

    outfd = open('{}.h'.format(opts.output), 'w')
    print( '/*')
    print( ' * Font {}'.format(fontName))
    print( ' */')
    print( '')
    print( '#define {}_HEIGHT {}'.format(fontName.upper(),height))
    print( '')

    yind = 0
    line = {}
    #for item in pixels:
    for yind in range(0,height):
        try:
            item = pixels.next()
        except:
            break
        print('{}: {}'.format(yind,item))
        line[yind] = []
        for xind in xrange(0,len(item),3):
            line[yind].append(dict(r=item[xind+0], g=item[xind+1], b=item[xind+2]))
            #line[yind].append(dict(r=item[xind+0], g=item[xind+1], b=item[xind+2], a=item[xind+3]))
        print('{}: {}'.format(yind,line[yind]))
        yind += 1
        if yind >= height:
            break

    asciiPixel = [' ', '.', '*', '*',
                  '*', '*', '*', '*',
                  '*', '*', '*', '*',
                  '*', '*', '*', '*']

    count = 0
    glyphData = {}
    glyphData[ch] = []
    offset = 0
    print( "const uint8_t {}_{:#x}[] __attribute__((__progmem__)) = {{   /* '{}' width: {} */".format(fontName,ord(ch), ch, width))

    x = 0
    for y in range(0,height):
        patt = ''
        print( '    ')
        lineWidth = 1
        pixels = 0
        pixCount = 0
        for x in range(0,width):
            count += 1
            # map 255 shades to 4
            pix = line[y][x]['r'] >> (8-opts.depth)
            pixels = pixels << opts.depth | pix
            pixCount += 1
            if pixCount >= (8/opts.depth):
                lineWidth += 1
                print( '0x{:02x}, '.format(pixels))
                glyphData[ch].append(pixels & 0xFF)
                pixels = 0
                pixCount = 0

            patt += asciiPixel[pix]

        count += 1
        pix = line[y][x+1]['r'] >> (8-opts.depth)
        patt += asciiPixel[pix]
        pixels = pixels << (opts.depth) | pix
        pixCount += 1
        if pixCount < (8/opts.depth):
            pixels = pixels << ((8/opts.depth)-pixCount)
        print( '0x{:02x}, '.format(pixels))
        glyphData[ch].append(pixels & 0xFF)
        #glyphData[ch].append((pixels >> 8) & 0xFF)
        if lineWidth < (maxWidth+3)/4:
            for ind in range(lineWidth, (maxWidth+3)/4):
                print( '      ')
        print( ' /* [{}] */'.format(patt))
    print( '};\n')
    print( '')

def generateHeader(fontName, pngFilename, xmlFilename):
    ''' Output C code tables for the specified font
    '''
    font = png.Reader(pngFilename)
    xml = ET.parse(xmlFilename)

    chars = xml.findall('Char')
    root = xml.getroot()
    glyphd = {}
    maxWidth = 0
    for char in chars:
        glyphd[ord(char.attrib['code'])] = char.attrib
        if int(char.attrib['width']) > maxWidth:
            maxWidth = int(char.attrib['width'])

    width, height, pixels, meta = font.asDirect()

    outfd = open('{}.h'.format(opts.output), 'w')
    print( '/*')
    print( ' * Font {}'.format(fontName))
    print( ' */')
    print( '')
    print( '#define {}_HEIGHT {}'.format(fontName.upper(),root.attrib['height']))
    print( '')

    yind = 0
    line = {}
    for item in pixels:
        line[yind] = []
        for xind in xrange(0,len(item),4):
            #line[yind].append(np.reshape(item, (128,4)))
            line[yind].append(dict(r=item[xind+0], g=item[xind+1], b=item[xind+2], a=item[xind+3]))
        yind += 1

    asciiPixel = [' ', '.', '*', '*',
                  '*', '*', '*', '*',
                  '*', '*', '*', '*',
                  '*', '*', '*', '*']
    count = 0
    glyphData = {}
    for ch in sorted(glyphd.keys()):
        if ch == ord(' '):
            # skip space
            continue
        glyph = glyphd[ch]
        glyphData[ch] = []
        rect = [int(x) for x in glyph['rect'].split()]
        offset = [int(x) for x in glyph['offset'].split()]
        print( 'const uint8_t {}_{:#x}[] __attribute__((__progmem__)) = {{'.format(fontName,ord(glyph['code'])))
        try:
            print( "  /* '{0}' width: {1} */".format(glyph['code'],glyph['width']))
        except:
            print( "  /* '?' width: {} */".format(glyph['width']))
        x = 0
        for y in range(rect[1],rect[1]+rect[3]):
            patt = ''
            print( '    ')
            lineWidth = 1
            pixels = 0
            pixCount = 0
            for x in range(rect[0],rect[0]+rect[2]-1):
                count += 1
                # map 255 shades to 4
                pix = line[y][x]['a'] >> (8-opts.depth)
                pixels = pixels << opts.depth | pix
                pixCount += 1
                if pixCount >= (8/opts.depth):
                    lineWidth += 1
                    print( '0x{:02x}, '.format(pixels))
                    glyphData[ch].append(pixels & 0xFF)
                    #glyphData[ch].append((pixels >> 8) & 0xFF)
                    pixels = 0
                    pixCount = 0

                patt += asciiPixel[pix]

            count += 1
            pix = line[y][x+1]['a'] >> (8-opts.depth)
            patt += asciiPixel[pix]
            pixels = pixels << (opts.depth) | pix
            pixCount += 1
            if pixCount < (8/opts.depth):
                pixels = pixels << ((8/opts.depth)-pixCount)
            print( '0x{:02x}, '.format(pixels))
            glyphData[ch].append(pixels & 0xFF)
            #glyphData[ch].append((pixels >> 8) & 0xFF)
            if lineWidth < (maxWidth+3)/4:
                for ind in range(lineWidth, (maxWidth+3)/4):
                    print( '      ')
            print( ' /* [{}] */'.format(patt))
        print( '};\n')
    print( '')

    # font header:
    #
    #    uint8_t height;         //*< height of font
    #    uint8_t fixedWidth;     //*< width of font, 0 = proportional font
    #    uint8_t depth;          //*< Number of bits per pixel
    #    const uint8_t *map;     //*< ASCII to font map
    #    union
    #    {
    #        const glyph_t *glyphs;   //*< variable width font data
    #        const uint8_t *bitmaps;  //*< fixed width font data
    #    } fontData;

    bfd = open('{}.img'.format(opts.output), "wb")

    #
    # binary header
    #
    fixedWidth = 0

    glyphCount = len(glyphData)
    if ord(' ') in glyphd:
        glyphCount += 1   # add 1 for space character

    # Can't handle 2 byte characters yet, so skip them
    for char in glyphData.keys():
        if char > 254:
            print('skipping extended character 0x{:x}'.format(char))
            glyphCount -= 1

    print( '{} glyphs'.format(glyphCount))
    header = pack('=BBBB', int(root.attrib['height']), fixedWidth, opts.depth, glyphCount)
    bfd.write(header)

    if opts.debug:
        print( 'XXX header: {}'.format(['0x{:02x}'.format(item) for item in bytearray(header)]))

    # map
    index = 0
    chMap = []
    glyphHeader = {}
    glyphOffset = 0
    glyphHeaderStr = ''
    for ch in range(ord(' '), 255):
        if glyphd.has_key(ch):
            chMap.append(index)
            index += 1
            glyph = glyphd[ch]
            rect = [int(x) for x in glyph['rect'].split()]
            offset = [int(x) for x in glyph['offset'].split()]
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
                glyphOffset += len(glyphData[ch])
        else:
            chMap.append(None)

    glyphMap = []

    print( '/* Mapping from ASCII codes to font characters, from space (0x20) to del (0x7f) */')
    print( 'const uint8_t {}_asciimap[{}] __attribute__((__progmem__)) = {{ '.format(fontName,len(chMap)))
    index = 0
    for item in chMap:
        if index == 0:
            print( '\n    ')
            index = 16
        if item != None:
            glyphMap.append(item)
            print( '{:>3}, '.format(item))
        else:
            glyphMap.append(255)
            print( '255, ')
        index -= 1
    print( '};\n')

    if len(chMap) < 256:
        glyphMap.extend([255 for i in range(0, 256-len(chMap))])


    #
    # binary ASCII map table
    #
    binaryData = bytearray(glyphMap)
    bfd.write(binaryData)
    if opts.debug:
        print( "XXX glyphMap: {}".format(['0x{:02x}'.format(item) for item in bytearray(glyphMap)]))

    #
    # binary glyph header data
    #
    index = 0
    for ch in range(ord(' '), 255):
        if glyphd.has_key(ch):
            bfd.write(glyphHeader[ch])
            if opts.debug:
                if ch < 127:
                    print( "XXX '{}' hdr[{}]: {}".format(chr(ch), index, ['0x{:02x}'.format(item) for item in bytearray(glyphHeader[ch])]))
                else:
                    print( "XXX {} hdr[{}]: {}".format(ch, index, ['0x{:02x}'.format(item) for item in bytearray(glyphHeader[ch])]))
            index += 1

    # glyph_t

    print( 'const glyph_t {}[] __attribute__((__progmem__)) = {{'.format(fontName))

    print( glyphHeaderStr)

    print( '};\n')

    #
    # binary glyph data
    #
    offset = 0
    for ch in sorted(glyphd.keys()):
        if ch == ord(' '):
            # skip space
            continue
        # convert glyph data to uint16_t packed data
        binaryData = bytearray(glyphData[ch])
        bfd.write(binaryData)
        if opts.debug:
            if ch < 127:
                print( "XXX 0x{:04x} '{}' data: {}".format(offset,chr(ch),['0x{:02x}'.format(item) for item in bytearray(glyphData[ch])]))
            else:
                print( "XXX 0x{:04x} {} data: {}".format(offset,ch,['0x{:02x}'.format(item) for item in bytearray(glyphData[ch])]))
        offset += len(glyphData[ch])

    bfd.close()
    outfd.close()
    print( 'wrote header font to {}.h'.format(opts.output))
    print( 'wrote binary font to {}.img'.format(opts.output))
    return count

def main():
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ%$'
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
            '$': 'dolar',
            }
    if opts.ttf:
        glyphs = fontforge.open(opts.ttf)
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
                filename = 'output/' + name + ".png"
                print( '0x{:x}: {:17} -> {}'.format(glyphs[ind].originalgid, name, filename))
                glyphs[ind].export(filename, 20, 6)
                #glyphs[ind].export(filename, 20, 6)
                generateGlyphHeader('test', name, filename)
                return
        return

    generateHeader(opts.name, opts.png, opts.xml)

if __name__ == "__main__":
    main()
