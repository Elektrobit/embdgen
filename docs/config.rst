YAML Config Interface
=====================

Introduction
------------

The configuration interfaces using a YAML file is implemented in the plugin embdgen-config-yaml.
This can load a configuration file and run embdgen to generate an image.
The idea is to describe an image in a hierarchial structure in a declarative format.
A :ref:`label <label>` is the root of this hierarchy. It can be an :ref:`MBR <label-mbr>` or :ref:`GPT <label-gpt>` partition table.

One label consists of multiple :ref:`regions <region>`. A region can but does not have to be part of the partition table.
This can be useful, for example, when the bootloader requires data at a specific address.

Every region is filled with :ref:`content <content>`. A content can be everything, that is written to the image.
Some contents are containers for other contents, so that the data written to image is transformed or enhanced with metadata for example.
Examples for these staggered contents are:
 
 - An :ref:`ext4 filesystem content <content-ext4>` which is created from an :ref:`archive content <content-archive>`
 - A :ref:`raw filesystem image <content-raw>` with added :ref:`verity metadata <content-verity>`


If a content (for example an archive) is split up into multiple contents, a :ref:`generator <generator>` has to be used.
In that case the root of the yaml document is split up into a ``contents`` and an ``image`` node.
See section `Content Generator Example`_.



Simple Example
--------------

Every element in the tree is YAML sequence, that contains a scalar ``type``, that identifies the implementation.

.. literalinclude:: examples/simple.yml
    :language: YAML
    :linenos:
    :caption: simple example
    :lines: 8-

The example above would create a master boot record partition table, with two partition entries (boot and root).
This fat32 boot partition is created by embdgen and contains a single file (fitimage).
The root partition is an ext4 partition, that is filled with a partition image, that already contains an ext4 filesystem.
Three additional partitions are created, that are not recorded in the partition table.
This setup is an example for the bootloader requirements the NXP's S32 series of SoCs:

 - uboot part 1 and 2: Write NXP specific code (i.e. the image vector table with its payload uboot and atf) around the partition table (between byte 256 and 512)
 - uboot.env: Creates an unused range (type: empty) between 0x1e0000 and 0x1e2000, which is the default area, where NXP's u-boot writes its environment


To generate the image, the embdgen can be executed from the directory where the config file is stored and the files directory with the referenced files exist.
Assuming the yaml config is save as config.yml::

    $ embdgen config.yml
    Preparing...

    The final layout:
    MBR:
      0x00000000 - 0x00000100 Part u-boot part 1
        RawContent(files/fip.s32@0x00000000)
      0x000001b8 - 0x00000200 Part MBR Header
      0x00000200 - 0x000fead0 Part u-boot part 2
        RawContent(files/fip.s32@0x00000200)
      0x001e0000 - 0x001e2000 Part uboot.env
      0x001e2000 - 0x065e2000 Part boot
        Fat32Content()
      0x065e2000 - 0x1c0e3000 Part root
        RawContent(files/root.raw@0x00000000)

    Writing image to image.raw

The tool prints out the final layout of all Regions.
There is now one more region than defined in the config file ("MBR Header").
This is inserted by the MBR label, to reserve the area where the partition table is written to.
For the boot and root partition no start addresses were defined in the config file, so these addresses are calculated automatically to the next free offset in the image.

Content Generator Example
-------------------------

.. literalinclude:: examples/generator.yml
    :language: YAML
    :linenos:
    :caption: generator example

This example uses the :ref:`split archive content generator <generator-split_archive>`, to split the archive in `files/archive.tar` into three separate contents
and assigns names to these contents according to the name of the module used (*archive*) and the name of split and the ``remaining`` property.

 - *archive.home* will contain the content of the directory *home* in the archive
 - *archive.data* will contain the content of the directory *data* in the archive
 - *archive.remaining* will contain all remaining files and empty folders for *home* and *data*

 The image definition will then create an image with three entries in the partition table.
 For the root partition dm verity metadata is created as well.

Reference
---------

This configuration reference is generated with all plugins loaded.

.. _label:

Label Types
-----------

.. embdgen-config:: embdgen.core.label.Factory
  :anchor: label

.. _region:

Region Types
------------

.. embdgen-config:: embdgen.core.region.Factory
  :anchor: region

.. _content:

Content Types
-------------

.. embdgen-config:: embdgen.core.content.Factory
  :anchor: content

.. _generator:

Content Generator Types
-----------------------

.. embdgen-config:: embdgen.core.content_generator.Factory
  :anchor: generator
