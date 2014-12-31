import shutil
import os
import pymclevel
import logging

logger = logging.getLogger(__name__)

saveFileDir = pymclevel.mclevelbase.saveFileDir

def getWorlds(srcPath, destPath=None, clean=False):
    srcPath = os.path.join(saveFileDir, srcPath)
    if destPath:
        destPath = os.path.join(saveFileDir, destPath)
    else:
        destPath = os.path.join(tempfile.gettempdir(), "mcprune" + str(src.RandomSeed))

    logger.info("Source: %s", srcPath)
    logger.info("Dest: %s", destPath)
    src = pymclevel.fromFile(srcPath, readonly=True)

    if clean and os.path.isdir(destPath):
        logger.info("Deleting target")
        shutil.rmtree(destPath)

    if not os.path.isdir(destPath):
        logger.info("Copying source")
        shutil.copytree(srcPath, destPath)

    return ( src, pymclevel.fromFile(destPath) )

regionSize = 32
def chunksInRegion(rx, rz):
    minX = rx * regionSize
    minZ = rz * regionSize

    chunkList = []
    for x in range(minX, minX + regionSize):
        for y in range(minZ, minZ + regionSize):
            chunkList.append((x, y))

    return chunkList

def defragRegion(src, dest, rx, rz):
    chunkList = set(dest.allChunks) & set(chunksInRegion(rx, rz))

    # ALL chunks must be deleted to get the file to be removed.
    for pos in chunkList:
        dest.deleteChunk(*pos)

    # Now copying all of the present chunks back in will regenerate
    # the file
    for cx, cz in chunkList:
        copyChunkAtPosition(src, dest, cx, cz)


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
