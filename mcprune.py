#!/usr/bin/env python
import getopt
import logging
import math
import sys
import utils

from pymclevel import materials

logger = logging.getLogger(__name__)

def extractBlockCount(level, blockCounts, blockID):
    block = level.materials.blockWithID(blockID, 0)
    if block.hasVariants:
        for data in range(16):
            i = (data << 12) + blockID
            if blockCounts[i]:
                return ( level.materials.blockWithID(blockID, data).name,
                    blockCounts[i]
                )

    else:
        count = int(sum(blockCounts[(d << 12) + blockID] for d in range(16)))
        if count:
            return (level.materials.blockWithID(blockID, 0).name,
                count
            )
    return (None, 0)

class McPrune:

    
    def __init__(self, srcName, destName, boundingBox):
        self.srcName = srcName
        self.destName = destName
        self.boundingBox = boundingBox
        self.targetSize = 500

    def uninhabitedMode(self, dest, chunk):
        return self.inhabitedBy(dest, chunk) is None

    def run(self, shouldDelete=None):
        if shouldDelete is None:
            shouldDelete = self.uninhabitedMode
        src, dest = utils.getWorlds(self.srcName, self.destName, clean=True)


        for i, (rx, rz) in enumerate(self.getRegions(dest), 1):
            percent = int((i / total * 100))
            if utils.defragRegion(src, dest, keepChunks, *lastRegion):
                sizeMB = utils.get_size(dest.worldFolder.filename)
                logger.info("Size: %s MB (%s%%)", sizeMB, percent)
                return sizeMB < self.targetSize
            else:
                logger.info("Region %s (%s%%)", lastRegion, percent)


        chunkList = self.getChunkList(dest)

        total = float(len(chunkList))
        lastRegion = None
        keepChunks = []

        def processRegion(lastRegion, keepChunks):
            percent = int((i / total * 100))
            if utils.defragRegion(src, dest, keepChunks, *lastRegion):
                sizeMB = utils.get_size(dest.worldFolder.filename)
                logger.info("Size: %s MB (%s%%)", sizeMB, percent)
                return sizeMB < self.targetSize
            else:
                logger.info("Region %s (%s%%)", lastRegion, percent)

        for i, pos in enumerate(chunkList, 1):
            cx, cz = pos

            if lastRegion and (cx >> 5, cz >> 5) != lastRegion:
                if processRegion(lastRegion, keepChunks):
                    lastRegion = None
                    break;
                keepChunks = []

            lastRegion = (cx >> 5, cz >> 5)
            chunk = dest.getChunk(cx, cz)
            if not shouldDelete(dest, chunk):
                keepChunks.append(pos)

        if lastRegion:
            processRegion(lastRegion, keepChunks)

        sizeMB = utils.get_size(dest.worldFolder.filename)
        logger.info("Final Size: %s MB", sizeMB)

    def getChunkList(self, dest):
        chunkList = list(dest.allChunks)
        logger.info("Total chunks in world: %s", len(chunkList))
        if self.boundingBox:
            logger.info("Bounding box: %s", self.boundingBox)
            x1, z1, x2, z2 = self.boundingBox

            # chunkList is a set of chunk coordinates, but the boundingBox is
            # in block coordinates. x and z are multiplied by 16 to convert the
            # chunks to block coordinates for comparison with the bounding box.
            chunkList = [(x, z) for x, z in chunkList 
                if (x1 <= (x*16) <= x2) and (z1 <= (z*16) <= z2) ]

        logger.info("Chunks to process: %s", len(chunkList))

        return self.prioritizeChunks(dest, chunkList)

    def prioritizeChunks(self, dest, chunkList):
        def chunkToRegion(pos):
            return (pos[0] >> 5, pos[1] >> 5)

        spawnRX = dest.root_tag['Data']['SpawnX'].value >> 5
        spawnRZ = dest.root_tag['Data']['SpawnZ'].value >> 5
        def sortKey(pos):
            '''
            '''
            rx, rz = chunkToRegion(pos)
            distX = (rx - spawnRX)
            distZ = (rz - spawnRZ)
            dist = int(math.sqrt( (distX * distX) + (distZ * distZ)))

            return (dist, rx, rz)

        # chunkList.sort(key=chunkToRegion)
        chunkList.sort(key=sortKey, reverse=True)
        return chunkList

        last = None
        for pos in map(chunkToRegion, chunkList):
            if last != pos:
                last = pos
                print pos

        return []


        return chunkList



    def inhabitedBy(self, level, chunk):
        allowedEntities = [
            "Cow",
            "Sheep",
            "Chicken",
            "Pig",
            "Rabbit",

            # These should decay naturally, so don't block a chunk from being
            # remove if they are present.
            "Arrow",
            "Item",
            "XPOrb",

            # Mobs despawn when the player is too far away. I don't see any
            # reason to keep these.
            "Bat",
            "Creeper",
            "Enderman",
            "Guardian",
            "Ozelot",
            "Skeleton",
            "Spider",
            "Squid",
            "Witch",
            "Wolf",
            "Zombie",

            # These are spawned naturally in mines, let them regenerate.
            "MinecartChest",

            # IDK how this exists long enough to get saved in the world.
            "FallingSand",
        ]
        for e in chunk.Entities:
            if allowedEntities.count(e["id"].value):
                continue
            return e["id"].value

        allowedTiles = [
            "Chest"
            "MobSpawner",
        ]
        for e in chunk.TileEntities:
            if allowedTiles.count(e["id"].value):
                continue
            return e["id"].value

        name, count = onlyNaturalBlocks(level, chunk)
        if count > 0:
            return name
        return None

        blockIds = [
            # 50, # torch
            # 85, # Fence
            54, 146, 4, 20, 23, 25, 26, 27, 28, 29, 33, 34, 35, 41, 42, 43, 44, 45, 47,
            53, 55, 58, 61, 62, 63, 64, 65, 67, 68, 69, 70, 71, 72, 75, 76, 77, 80, 84,
            92, 93, 94, 95, 96, 98, 101, 102, 107, 108, 109, 114, 116, 117, 123, 124,
            130, 134, 135, 136, 139, 140, 143, 145, 147, 148, 149, 150, 151, 152, 154,
            155, 156, 157, 158, 160, 163, 167, 170, 171, 173, 176, 177, 178, 180, 181,
            183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196
        ]
        bc = utils.getBlockCounts(chunk)
        for id in blockIds:
            name, count = extractBlockCount(level, bc, id)
            if count > 0:
                return name

        return None

naturalBlocks = [
    # Even though these can be spaned naturally, they are commonly used in
    # builds by players.
    #
    # (4), # Cobblestone
    # (5,0), # Oak planks
    # (54,2), (54,3), (54,4), (54,5), # Chests
    # (85), # fence

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
]

def onlyNaturalBlocks(level, chunk):
    blockCounts = utils.getBlockCounts(chunk)
    for blockID in range(materials.id_limit):
        block = level.materials.blockWithID(blockID, 0)
        if block.hasVariants:
            for data in range(16):
                if (blockID, data) in naturalBlocks:
                    continue
                i = (data << 12) + blockID
                if blockCounts[i]:
                    return ( level.materials.blockWithID(blockID, data).name,
                        blockCounts[i]
                    )
        else:
            if (blockID) in naturalBlocks:
                continue
            count = int(sum(blockCounts[(d << 12) + blockID] for d in range(16)))
            if count:
                return ( level.materials.blockWithID(blockID, 0).name,
                    blockCounts[i]
                )
    return (None, 0)


def _convertToBoundingBox(value):
    boundingBox = map(int, value.split(' '))

    if len(boundingBox) != 4:
        raise ValueError("Bounding box: must be 4 numbers")

    x1, z1, x2, z2 = boundingBox
    return ( min(x1, x2), min(z1, z2), max(x1, x2), max(z1, z2))

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

    McPrune(args[0], args[1], boundingBox).run()

if __name__ == "__main__":
   main(sys.argv[1:])

