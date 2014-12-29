The goal of this project is to remove chunks that were generated, but are
otherwise untouched by players. This *should* reduce the file size of the world
without impacting play because the chunks will just get regenerated if a player
ever returns. Simply selecting areas in MCEdit and pruning the world is
insufficent as I don't want to kill off the builds that I've never been to ans
aren't sure where they are.

Minecraft Realms has a restriction that your uploaded world must be less than
500MB.

How to install
==============

If you know how to make this work please submit a pull request. I'm new to
Python and installing 3rd party libraries doesn't make any sense to me.

Approaches I have tried
=======================

This seems like a pretty straighforward task, but has proven to be surprisingly
difficult.

Remove uninhabited chunks
-------------------------

I whitelisted a set of Entities and TileEntities, and then blacklisted a set of
blocks that don't (or uncommonly) generate natrually. The result was that it
simply poked holes in the world and failed to reduce the file size.

My list of blacklisted blocks was modified from
[minecraft-chunk-deleter][chunk-deleter].


Compare with clean world
------------------------

1. Copy the source world
2. Generate a list of chunks
3. Delete all chunks in the copy (so it has the same seed)
4. Regenerate all of the chunks in the new world.
5. Remove any chunks that are identical in both worlds.

I'm assuming this approach failed because things like trees will generate
randomly during world generation. It also just poked holes in the world and
failed to reduce the file size.

Whitelist blocks
----------------

1. Generate a sample world with a few thousand chunks
2. Analyze the world to produce a list of naturally occuring blocks.
3. Remove blocks commonly used in player builds
  * Cobblestone
  * Oak planks
  * Chests
  * fence
4. Delete all chunks that contain only naturally occuring blocks.

Again... it just poked holes in the world and failed to reduce the file size.


[chunk-deleter]: https://code.google.com/p/minecraft-chunk-deleter/
