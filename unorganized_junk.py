#!/usr/bin/env python

import csv
import getopt
import json
import logging
import materials
import mclevel
import numpy
import os.path
import shutil
import sys
import tempfile

from Queue import Queue
from minecraft_server import MCServerChunkGenerator
from numpy import zeros, bincount
from threading import Thread

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


def getChunkList(level):
    return list(level.allChunks)

def cleanWorld(dest, chunkList):
    removeChunks(dest, chunkList)
    gen = MCServerChunkGenerator()
    gen.generateChunksInLevel(dest, chunkList)


def getIdenticalChunks(src, dest):
    identical = []
    percent = 0
    total = src.chunkCount / 100
    for count, chunk in enumerate(src.getChunks()):
        try:
            cleanChunk = dest.getChunk(*chunk.chunkPosition)
        except Exception, e:
            continue

        countA = getBlockCounts(chunk)
        countB = getBlockCounts(cleanChunk)
        if numpy.array_equiv(countA, countB):
            identical.append(chunk.chunkPosition)

        if (count / total) != percent:
            percent = count / total
            print percent, count, len(identical)


    return identical

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

def removeChunks(dest, toRemove):
    total = len(toRemove)
    percent = 0
    for count, pos in enumerate(toRemove):
        if (count / total) != percent:
            percent = count / total
            print percent, count
        dest.deleteChunk(*pos)
    dest.saveInPlace()

def onlyNaturalBlocks(level, chunk):
    blockCounts = getBlockCounts(chunk)
    for blockID in range(materials.id_limit):
        block = level.materials.blockWithID(blockID, 0)
        if block.hasVariants:
            for data in range(16):
                if naturalBlocks.count((blockID, data)) > 0:
                    continue
                i = (data << 12) + blockID
                if blockCounts[i]:
                    return False
        else:
            if naturalBlocks.count((blockID)) > 0:
                continue
            count = int(sum(blockCounts[(d << 12) + blockID] for d in range(16)))
            if count:
                return False
    return True

def analyze(level):
    """
    analyze

    Counts all of the block types in every chunk of the world.
    """
    blockCounts = zeros((65536,), 'uint64')
    sizeOnDisk = 0

    print "Analyzing {0} chunks...".format(level.chunkCount)
    # for input to bincount, create an array of uint16s by
    # shifting the data left and adding the blocks

    for i, cPos in enumerate(level.allChunks, 1):
        ch = level.getChunk(*cPos)
        btypes = numpy.array(ch.Data.ravel(), dtype='uint16')
        btypes <<= 12
        btypes += ch.Blocks.ravel()
        counts = bincount(btypes)

        blockCounts[:counts.shape[0]] += counts
        if i % 100 == 0:
            logging.info("Chunk {0}...".format(i))

    for blockID in range(materials.id_limit):
        block = level.materials.blockWithID(blockID, 0)
        if block.hasVariants:
            for data in range(16):
                i = (data << 12) + blockID
                if blockCounts[i]:
                    idstring = "({id}:{data})".format(id=blockID, data=data)

                    print "{idstring:9} {name:30}: {count:<10}".format(
                        idstring=idstring, name=level.materials.blockWithID(blockID, data).name, count=blockCounts[i])

        else:
            count = int(sum(blockCounts[(d << 12) + blockID] for d in range(16)))
            if count:
                idstring = "({id})".format(id=blockID)
                print "{idstring:9} {name:30}: {count:<10}".format(
                      idstring=idstring, name=level.materials.blockWithID(blockID, 0).name, count=count)

###################################################################33


# logging.basicConfig(level=logging.DEBUG)

minInhabited = -1

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



def getBlockCounts(chunk):
    blockCounts = zeros((65536,), 'uint64')

    ch = chunk

    btypes = numpy.array(ch.Data.ravel(), dtype='uint16')
    btypes <<= 12
    btypes += ch.Blocks.ravel()
    counts = bincount(btypes)

    blockCounts[:counts.shape[0]] += counts

    return blockCounts

def foo(level, blockCounts, blockID):
    block = level.materials.blockWithID(blockID, 0)
    if block.hasVariants:
        for data in range(16):
            i = (data << 12) + blockID
            if blockCounts[i]:
                idstring = "({id}:{data})".format(id=blockID, data=data)
                print "{idstring:9} {name:30}".format(
                      idstring=idstring, name=level.materials.blockWithID(blockID, data).name)
                return blockCounts[i]

    else:
        count = int(sum(blockCounts[(d << 12) + blockID] for d in range(16)))
        if count:
            idstring = "({id})".format(id=blockID)
            print "{idstring:9} {name:30}".format(
                  idstring=idstring, name=level.materials.blockWithID(blockID, 0).name)
            return count
    return 0


allowedEntities = [
    "Bat",
    "Creeper",
    "Enderman",
    "Skeleton",
    "Witch",
    "Zombie",
    "Guardian",
    "Squid",
    "Spider",
    "Wolf",
    "Ozelot",
    "XPOrb",
    "MinecartChest",
    "Item",
    "FallingSand"

]
allowedTiles = [
    "MobSpawner",
    "Chest"
]
def uninhabited(level, chunk):
    for e in chunk.Entities:
        if allowedEntities.count(e["id"].value):
            continue
        print "{idstring:9} {name:30}".format(
            idstring="(0:e)", name=e["id"].value)
        return False

    for e in chunk.TileEntities:
        if allowedTiles.count(e["id"].value):
            continue
        print "{idstring:9} {name:30}".format(
            idstring="(0:t)", name=e["id"].value)
        return False

    bc = getBlockCounts(level, chunk)
    for id in blockIds:
        if foo(level, bc, id):
            return False

    return True

def listBlocks(level):
    for blockID in blockIds:
        idstring = "({id})".format(id=blockID)
        print "{idstring:9} {name:30}".format(
              idstring=idstring, name=level.materials.blockWithID(blockID, 0).name)



def equalChunks(a, b):
    return numpy.array_equal(a.Data, b.Data)

def worker(q, chunks):
    while True:
        item = q.get()
        if numpy.array_equal(item[0], item[1]):
            chunks.append(item[2])
        q.task_done()

def usage():
    print "Usage: HA HA!"

class Operations:
    pass


def main():
    srcPath = "/tmp/sourceworld"
    src, dest = getWorlds(srcPath)

    print  src.chunkCount, dest.chunkCount

    deleted = 0
    chunkList = getChunkList(src)
    total = float(len(chunkList))
    for count, pos in enumerate(chunkList, 1):
        if count % 100 == 0:
            percent = int(deleted / float(count) * 100)
            print "{0}/{1} {2}/{3} {4}%".format(count, int(total), deleted, count, percent)

        try:
            chunk = dest.getChunk(*pos)
        except Exception, e:
            continue

        if onlyNaturalBlocks(dest, chunk):
            deleted += 1
            dest.deleteChunk(*pos)

    dest.saveInPlace()
    return

    # cleanWorld(dest, chunkList)

    analyze(dest)
    return

    identical = getIdenticalChunks(src, dest)
    # removeChunks(dest, identical)

    for count, chunk in enumerate(chunkList):
        if chunk not in identical:
            print count
            copyChunkAtPosition(src, dest, *chunk)

    return


    return
    level.deleteChunk(0, 0)
    level.saveInPlace()
    gen = MCServerChunkGenerator()
    gen.generateChunkInLevel(level, 0, 0)

    toRemove = []
    for count, chunk in enumerate(level.getChunks()):
        if uninhabited(level, chunk):
            toRemove.append(chunk.chunkPosition)

        if (count / total) != percent:
            percent = count / total
            print percent, count

if __name__ == "__main__":
   main()
