#!/usr/bin/env python
import getopt
import logging
import math
import sys
import utils

from pymclevel import materials

logger = logging.getLogger(__name__)

def chunkToRegion(pos):
    return (pos[0] >> 5, pos[1] >> 5)

def extractBlockCount(level, blockCounts, blockID):
    block = level.materials.blockWithID(blockID, 0)
    if block.hasVariants:
        for data in xrange(16):
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

    def removeChunk(self, chunk):
        tmp = self.inhabitedBy(self.dest, chunk)

        # print (-122 >> 5, -8 >> 5), chunk.chunkPosition, tmp, (tmp is None)
        return tmp is None

    def run(self, clean=True):
        src, dest = utils.getWorlds(self.srcName, self.destName, clean=clean)
        self.dest = dest
        regionList = self.getRegions(dest)

        total = len(regionList)
        for i, (rx, rz) in enumerate(regionList, 1):
            percent = int( i / total * 100.0)

            if utils.defragRegion(src, dest, rx, rz, self.removeChunk):
                sizeMB = utils.get_size(dest.worldFolder.filename)
                logger.info("Size: %s MB (%s%%)", sizeMB, percent)
                if sizeMB < self.targetSize:
                    break;
            else:
                logger.info("Region %s (%s%%)", (rx, rz), percent)

        sizeMB = utils.get_size(dest.worldFolder.filename)
        logger.info("Final Size: %s MB", sizeMB)

    def getRegions(self, dest):
        regions = list(set(map(chunkToRegion, self.getChunkList(dest))))

        spawnRX = dest.root_tag['Data']['SpawnX'].value >> 5
        spawnRZ = dest.root_tag['Data']['SpawnZ'].value >> 5
        def sortKey(pos):
            distX = (pos[0] - spawnRX)
            distZ = (pos[1] - spawnRZ)
            dist = math.sqrt( (distX * distX) + (distZ * distZ))

            return dist

        regions.sort(key=sortKey, reverse=True)
        return regions

    def getChunkList(self, dest):
        print "total chunks:", len(list(dest.allChunks))

        if self.boundingBox:
            logger.info("Bounding box: %s", self.boundingBox)
            x1, z1, x2, z2 = self.boundingBox

            # chunkList is a set of chunk coordinates, but the boundingBox is
            # in block coordinates. x and z are multiplied by 16 to convert the
            # chunks to block coordinates for comparison with the bounding box.
            chunkList = [(x, z) for x, z in dest.allChunks
                if (x1 <= (x*16) <= x2) and (z1 <= (z*16) <= z2) ]
        else:
            chunkList = list(dest.allChunks)

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
            "Chest",
            "MobSpawner",
        ]
        for e in chunk.TileEntities:
            if allowedTiles.count(e["id"].value):
                continue
            return e["id"].value

        if onlyNaturalBlocks(level, chunk):
            return None
        return "Block"


naturalBlocks = [
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
]

def onlyNaturalBlocks(level, chunk):
    return utils.onlyNaturalBlocks(level, chunk)

    blockCounts = utils.getBlockCounts(chunk)

    # Instead of materials.id_limit which is the maximum possible ID I'm simply
    # stopping at 431 (Dar Oak Door).
    #
    # The music disks have much higher numbers, but they aren't blocks, so they
    # don't matter for this function.
    for blockID in xrange(431):

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
                return ((blockID, data), count)

    return (None, 0)


def _convertToBoundingBox(value):
    boundingBox = map(int, value.split(' '))

    if len(boundingBox) != 4:
        raise ValueError("Bounding box: must be 4 numbers")

    x1, z1, x2, z2 = boundingBox

    x1 = (x1 >> 4) << 4
    z1 = (z1 >> 4) << 4
    x2 = (x2 >> 4) << 4
    z2 = (z2 >> 4) << 4

    return ( min(x1, x2), min(z1, z2), max(x1, x2), max(z1, z2))

def usage():
    print "Usage: HA HA!"

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "h", [
            "help",
            "no-clean",
            "bounding-box="
        ])
    except getopt.GetoptError as err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    clean = True
    boundingBox = None
    for option, value in opts:
        if option == '--bounding-box':
            boundingBox = _convertToBoundingBox(value)
        if option == '--no-clean':
            clean = False

    McPrune(args[0], args[1], boundingBox).run(clean)

if __name__ == "__main__":
   main(sys.argv[1:])

