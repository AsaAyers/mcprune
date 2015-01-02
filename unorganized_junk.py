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
from threading import Thread



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


def analyze(level):
    """
    analyze

    Counts all of the block types in every chunk of the world.
    """
    blockCounts = numpy.zeros((65536,), 'uint64')
    sizeOnDisk = 0

    print "Analyzing {0} chunks...".format(level.chunkCount)
    # for input to bincount, create an array of uint16s by
    # shifting the data left and adding the blocks

    for i, cPos in enumerate(level.allChunks, 1):
        ch = level.getChunk(*cPos)
        btypes = numpy.array(ch.Data.ravel(), dtype='uint16')
        btypes <<= 12
        btypes += ch.Blocks.ravel()
        counts = numpy.bincount(btypes)

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
