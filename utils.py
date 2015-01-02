import logging
import math
import numpy
import os
import pymclevel
import shutil
import tempfile

logger = logging.getLogger(__name__)

saveFileDir = pymclevel.mclevelbase.saveFileDir

# http://stackoverflow.com/a/1392549/35247
def get_size(start_path = '.'):
    total_size = 0
    if os.path.isfile(start_path):
        total_size += os.path.getsize(start_path)

    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)

    return float("{0:.2f}".format(float(total_size) / 1024 / 1024))

def getWorlds(srcPath, destPath=None, clean=False):
    srcPath = os.path.join(saveFileDir, srcPath)
    src = pymclevel.fromFile(srcPath, readonly=True)
    if destPath:
        destPath = os.path.join(saveFileDir, destPath)
    else:
        destPath = os.path.join(tempfile.gettempdir(), "mcprune" + str(src.RandomSeed))

    logger.info("Source: %s", srcPath)
    logger.info("Dest: %s", destPath)

    if clean and os.path.isdir(destPath):
        logger.info("Deleting target")
        shutil.rmtree(destPath)

    if not os.path.isdir(destPath):
        logger.info("Copying source")
        shutil.copytree(srcPath, destPath)

    return ( src, pymclevel.fromFile(destPath) )

regionSize = 32
def getChunksInRegion(rx, rz):
    minX = rx * regionSize
    minZ = rz * regionSize

    chunkList = []
    for x in range(minX, minX + regionSize):
        for y in range(minZ, minZ + regionSize):
            chunkList.append((x, y))

    return chunkList

def defragRegion(src, dest, keepChunks, rx, rz):
    chunksInRegion = [ pos for pos in getChunksInRegion(rx, rz)
            if dest.containsChunk(*pos) ]

    cx, cz = chunksInRegion[0]
    srcPath = src.getRegionForChunk(cx, cz).path
    startSize = get_size(srcPath)
    if startSize <= 0.5:
        # Not enough gain in defragging very small regions.
        return False

    # ALL chunks must be deleted to get the file to be removed.
    for pos in chunksInRegion:
        dest.deleteChunk(*pos)

    totalChunks = 0
    # Now copying all of the keepChunks back in will regenerate the file
    for cx, cz in keepChunks:
        copyChunkAtPosition(src, dest, cx, cz)
        totalChunks += 1

    destPath = dest.getRegionForChunk(cx, cz).path

    percent = int( float(totalChunks) / len(chunksInRegion) * 100)
    if startSize >= get_size(destPath):
        logger.warn("Defrag %s, %s (%s MB -> %s MB) %s%%", rx, rz,
                startSize, get_size(destPath), percent)

        shutil.copy(srcPath, destPath)
    else:
        logger.info("Defrag %s, %s (%s chunks -> %s chunks) %s%%", rx, rz,
                len(chunksInRegion), totalChunks, percent)

    return True

def chunkListToRegionList(coords):
    return set([ (cx >> 5, cz >> 5) for cx, cz in coords ])

# From minecraft_server.py
def copyChunkAtPosition(tempWorld, level, cx, cz):
    if level.containsChunk(cx, cz):
        return
    try:
        tempChunkBytes = tempWorld._getChunkBytes(cx, cz)
    except ChunkNotPresent, e:
        raise ChunkNotPresent, "While generating a world in {0} using server {1} ({2!r})".format(tempWorld, e), sys.exc_info()[2]

    level.worldFolder.saveChunk(cx, cz, tempChunkBytes)
    level._allChunks = None


def getBlockCounts(chunk):
    blockCounts = numpy.zeros((65536,), 'uint64')

    ch = chunk

    btypes = numpy.array(ch.Data.ravel(), dtype='uint16')
    btypes <<= 12
    btypes += ch.Blocks.ravel()
    counts = numpy.bincount(btypes)

    blockCounts[:counts.shape[0]] += counts

    return blockCounts
