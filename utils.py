import logging
import math
import numpy
import os
import pymclevel
import shutil
import tempfile
import itertools

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
    cx = rx * regionSize
    cz = rz * regionSize

    return itertools.product(
        xrange(cx, cx + regionSize),
        xrange(cz, cz + regionSize)
    )


def defragRegion(src, dest, rx, rz, dropChunk=lambda x: False):
    posInRegion = [ pos for pos in getChunksInRegion(rx, rz) if dest.containsChunk(*pos) ]

    # posInRegion = list(dest.getChunks(getChunksInRegion(rx, rz)))

    if len(posInRegion) == 0:
        return False

    toKeep = [chunk for chunk in dest.getChunks(posInRegion) if not dropChunk(chunk)]
    if len(toKeep) == len(posInRegion):
        return False

    srcPath = src.worldFolder.getRegionFile(rx, rz).path
    startSize = os.path.getsize(srcPath)

    # 8192 seems to be the smallest possible region size.
    if startSize == 8192:
        logger.warn("Defrag skipping 8K region: (%s, %s) %s", rx, rz, srcPath)
        return False

    # ALL chunks must be deleted to get the file to be removed.
    for pos in posInRegion: 
        dest.deleteChunk(*pos)
    # deleteRegion(dest.worldFolder, rx, rz)

    totalChunks = 0
    # Now copying all of the keepChunks back in will regenerate the file
    for chunk in toKeep:
        srcChunk = src.getChunk(*chunk.chunkPosition)
        copyChunkAtPosition(src, dest, *srcChunk.chunkPosition)
        totalChunks += 1

    destPath = dest.worldFolder.getRegionFile(rx, rz).path

    destSize = os.path.getsize(destPath)
    if startSize <= destSize:
        logger.info("Defrag (FAIL) %s, %s (%s chunks -> %s chunks) (%s B -> %s B)",
                rx, rz,
                len(posInRegion), totalChunks,
                startSize, destSize)

        shutil.copy(srcPath, destPath)
        return False
    logger.info("Defrag %s, %s (%s chunks -> %s chunks) (%s B -> %s B)",
            rx, rz,
            len(posInRegion), totalChunks,
            startSize, destSize)

    return True

# adapted from pymclevel/infiniteworld.py deleteChunk
def deleteRegion(worldFolder, rx, rz):
    r = (rx, rz)
    rf = worldFolder.getRegionFile(*r)
    if rf:
        rf.close()
        os.unlink(rf.path)
        del worldFolder.regionFiles[r]

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
    # A chunk is a 16x16x256 array of Voxels. Each position can only hold a
    # single value. This preallocates the array to hold the result.
    blockCounts = numpy.zeros((65536,), 'uint64')


    # Due to legacy reasons the values are stored in two pieces. These combine
    # those two pieces into a set of values.
    #
    # These make btypes into an array of 65536 each containing a value anywhere
    # in the range of 0 - 69632 ((16 << 12) + 4096)
    btypes = numpy.array(chunk.Data.ravel(), dtype='uint16')
    btypes <<= 12
    btypes += chunk.Blocks.ravel()

    # numpy.bincount will count how many times each value occurs. If the value
    # 1 occurs 2000 times, then counts[1] == 2000.
    # counts.shape[0] == (max(btypes) + 1)
    counts = numpy.bincount(btypes)

    blockCounts[:counts.shape[0]] += counts

    return blockCounts

# I need to know if blockCounts contains any values that are not in my
# whitelist of values. This whitelist is non-continuous. (sample: 0, 2, 6, 32,
# 81, 106, 111)
#
# In my current method I can iterate over all of the potential values, skip any
# that match my whitelist and then exit early if blockCounts[x] > 0.
#
# Is there any shortcut I can use to check this without a loop in Python? It
# seems like if I could set blockCounts[0] = blockCounts[32] = blockCounts[81]
# = ... = 0 I could numpy.bincount(blockCounts) and then see if .shape[0] > 0.
#
# One thought I had was to generate a mask [0, 1, 0, 1, 1, 1, 0, ...] to ignore
# values in positions 0, 1, 6, ... but I'm having trouble finding a way to
# apply this idea.
#
# if I had such an applyMask function, it seems like this would work to tell me
# if the chunk contains any values that are NOT whitelisted.
#
# def onlyNaturalBlocks(level, chunk):
#     blockCounts = utils.getBlockCounts(chunk)
#     return numpy.bincount(applyMask(blockCounts, precalculatedMask)).shape[0] == 0
#
# Below is my very slow implementation that has to be run millions of times
# over a world. It currently takes hours to process a world with this.

naturalBlocks = set([
    # Even though these can be generated naturally, they are commonly used in
    # builds by players.
    #
    # (4), # Cobblestone
    # (5,0), # Oak planks
    # (54,2), (54,3), (54,4), (54,5), # Chests
    # (85), # fence

    (32), (81),
    (175, 8),
    (106),
    (6), (6, 1), (6, 2), (6, 3), (6, 4), (6, 5),
    (111),
    (3, 1),

    (0), (1,0), (9), (7), (1,5), (1,1), (1,3), (3,0), (13), (16), (2), (15),
    (11), (12,0), (73), (161,1), (162,1), (31,1), (18,8), (18,0), (161,9),
    (14), (97,0), (24,0), (78), (10), (21), (56), (18,10), (18,2), (17,0),
    (18,1), (18,9), (82), (129), (49), (175,10), (17,2), (175,2), (30), (66),
    (17,1), (48), (37), (175,0), (8), (38,0), (99,5), (38,8), (100,9), (100,7),
    (100,3), (100,1), (38,3), (100,10), (39), (100,8), (100,6), (100,4),
    (99,10), (100,2), (79), (40), (17,4), (175,1), (83), (99,8), (99,6),
    (99,2), (99,4), (38,5), (175,4), (99,9), (99,3), (99,7), (52), (175,5),
    (99,1), (100,5), (50), (17,8), (38,7), (38,6), (38,4), (86,3), (86,1),
    (86,0), (86,2)
])

allPossible = itertools.product(xrange(4096), xrange(16))
toCheck = [ (data << 12) + blockID for blockID, data in allPossible
    if (blockID) not in naturalBlocks and (blockID, data) not in naturalBlocks
]

allPossible = itertools.product(xrange(4096), xrange(16))
keepMask = [ (blockID) not in naturalBlocks and (blockID, data) not in naturalBlocks
    for blockID, data in allPossible
]

def _applyMask(x, keep):
    if keep:
        return x
    return 0
applyMask = numpy.frompyfunc(_applyMask, 2, 1)

def bad_onlyNaturalBlocks(level, chunk):
    blockCounts = getBlockCounts(chunk)
    numpy.sum(applyMask(blockCounts, keepMask)) == 0

def onlyNaturalBlocks(level, chunk):
    blockCounts = getBlockCounts(chunk)
    for i in toCheck:
        if blockCounts[i]:
            return False

    return True

def XonlyNaturalBlocks(level, chunk):
    blockCounts = getBlockCounts(chunk)

    for blockID in xrange(4096):

        if (blockID) in naturalBlocks:
            continue

        for data in xrange(16):
            if (blockID, data) in naturalBlocks:
                continue

            i = (data << 12) + blockID
            count = blockCounts[i]
            if count:
                # idstring = "({id}:{data})".format(id=blockID, data=data)
                # print "{idstring:9} {name:30}: {count:<10}".format( idstring=idstring, name=level.materials.blockWithID(blockID, data).name, count=count)
                return False

    return True
