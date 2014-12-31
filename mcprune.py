#!/usr/bin/env python
import getopt
import sys
import utils
import logging

logger = logging.getLogger(__name__)


def foo(chunks, x1, z1, x2, z2):
    return [(x, z) for x, z in chunks if (x1 < x < x2) and (z1 < z < z2) ]

class McPrune:
    
    def __init__(self, srcName, destName, boundingBox):
        self.src, self.dest = utils.getWorlds(srcName, destName, clean=True)
        self.chunkList = list(self.dest.allChunks)
        logger.info("Total chunks in world: %s", len(self.chunkList))
        if boundingBox:
            logger.info("Bounding box: %s", boundingBox)
            x1, z1, x2, z2 = boundingBox
            self.chunkList = [(x, z) 
                for x, z in self.chunkList if (x1 < x < x2) and (z1 < z < z2) ]

        logger.info("Chunks to process: %s", len(self.chunkList))


def _convertToBoundingBox(value):
    boundingBox = map(int, value.split(' '))

    if len(boundingBox) != 4:
        raise ValueError("Bounding box: must be 4 numbers")

    x1, z1, x2, z2 = boundingBox
    if (x2 <= x1) or (z2 <= z1):
        print x2, x1
        print z2, z1

        raise ValueError("Bounding box: Invalid format")

    return boundingBox

def usage():
    print "Usage: HA HA!"

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "h", [
            "help",
            "bounding-box="
        ])
    except getopt.GetoptError as err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    boundingBox = None
    for option, value in opts:
        if option == '--bounding-box':
            boundingBox = _convertToBoundingBox(value)

    McPrune(args[0], args[1], boundingBox)
    args = args[2:]

if __name__ == "__main__":
   main(sys.argv[1:])

