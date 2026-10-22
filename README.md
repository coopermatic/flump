# Flump

Flump reads specially-constructed `.fla` and `.xfl` files saved by Flash and extracts animations and
textures to allow them to be recreated in the GPU. Animations created in Flump's style will use far
less texture memory per frame of animation than an equivalent flipbook animation, allowing for more
expressive animations on mobile platforms. Runtimes have been written for [Starling], [Sparrow],
[Flambe], [PlayN], and [StageXL].

[Starling]: https://github.com/threerings/flump/tree/master/runtime
[Sparrow]: https://github.com/threerings/betwixt
[Flambe]: https://github.com/aduros/flambe
[PlayN]: https://github.com/threerings/tripleplay
[StageXL]: http://www.stagexl.org/index.html

# Creating a movie for Flump

1. Install a validated Flump build. See [build and installation instructions](docs/BUILDING.md).
   The historical shared-runtime `.air` release is retained, but is not a native Apple Silicon build.
2. Create a `.fla` in Flash CS 5, 5.5, or 6.
3. Create a new item in the library and draw a shape in its canvas.
4. Right-click on the item, select its properties, tick the **Export for ActionScript** and
   **Export in frame 1** checkboxes and change its base class to `flash.display.Sprite`.
5. Create a second item in the library, and drag the first into it.
6. Add additional frames in the second item, and create a classic tween moving the first item around
   in those frames.
6. Set the **Export for ActionScript** and **Export in frame 1** properties for the second item. Leave its base class as `flash.display.MovieClip`.
7. Save the file and publish it as a swf.
8. Open the Flump app and change its import directory to the directory containing the `.fla` and
   `.swf` files. The `.fla` file should appear in the list of source files.
9. Select the `.fla` file and click 'Preview'. The tween you created in step 6 should start playing
   back in a preview window.

# Details of Flump's conversion

This walks through Flump's process when it exports a single .fla/.swf file combo.

### Texture creation

For each item in the document's library that is exported for ActionScript and extends
`flash.display.Sprite`, Flump creates a texture. To do so, it instantiates the library's exported
symbol from the `.swf` file and renders it to a bitmap.

All of the created bitmaps for a Flash document are packed into texture atlases, and xml is
generated to map between a texture's symbol and its location in the bitmap.

### Animation creation

For each item in the document's library that extends `flash.display.MovieClip` and isn't a flipbook
(explained below), Flump creates an animation. It checks that for all layers and keyframes, each
used symbol is either a texture, an animation, or a flipbook. Flump animations can only be
constructed from the flump types.

### Flipbook creation

For animations that only contain a few frames, a flipbook may be more appropriate. To create one,
add a new item to the library and name the first layer in the created item `flipbook`. When
exporting, flump will create a bitmap for each keyframe in the flipbook layer. In playback, flump
will display those bitmaps at the same timing.

### Compatibility

Flump works with Flash CS 5 and later

# Precompiled binaries

The fork's previous `.air` and `.swf` are preserved in `exporter/dist` for comparison.
[Historical upstream releases](https://github.com/threerings/flump/releases/latest) are also available.
Neither should be assumed to run natively on Apple Silicon. New candidate builds go in
`exporter/build`; validate them before replacing a working installation.

# Building

See [BUILDING.md](docs/BUILDING.md) for the pinned Flex/AIR toolchain, Windows and macOS builds,
signing and notarisation, fixture tests, export comparisons and M4 native-process verification.
The [audit and validation record](docs/AUDIT.md) distinguishes verified results from pending tests.
For the internal Apple Silicon ZIP built on GitHub from Windows, see
[Mac distribution](docs/MAC-DISTRIBUTION.md). AIR licensing must be confirmed; Apple
Developer ID signing and notarisation remain optional future distribution routes.
For Mac distribution from Windows, use the [GitHub Actions and signing setup](docs/MAC-DISTRIBUTION.md).
The designer only installs and tests the supplied package; all build steps belong to the build owner.

With Java, Ant, `FLEX_HOME` (Flex 4.16.1 with a matching AIR overlay) and `AIR_HOME` configured:

```sh
ant -f exporter/build.xml verify-libs
ant -f exporter/build.xml swf test
# Configure existing AIR signing credentials as described in BUILDING.md first:
ant -f exporter/build.xml bundle-windows   # on Windows
# On macOS, use bundle-macos with your existing Developer ID Application identity.
```

The exporter uses the six existing SWCs in `exporter/lib`; rebuilding or deploying the runtime
and demo is unnecessary. Application source, fixtures and old releases are preserved.
For the smallest initial Mac migration test, `repackage-macos` wraps the preserved release in a
current signed universal AIR runtime without recompiling; see BUILDING.md for the full command.
        
# Runtimes

A list of known Flump runtime implementations for different languages and frameworks:

* [Flump (Starling/AS3)](https://github.com/tconkling/flump) (the reference runtime, contained here)
* [Flambe (Haxe)](https://github.com/aduros/flambe)
* [pixi-flump-runtime (Haxe/PixiJs)](https://github.com/jackwlee01/pixi-flump-runtime)
* [StageXL_Flump](https://github.com/bp74/StageXL_Flump) (Dart / HTML5 / WebGL / Canvas)
* [Betwixt (Sparrow/Objective-C)](https://github.com/threerings/betwixt) (no longer maintained)
* [pixi-flump](https://github.com/mientjan/pixi-flump) (Javascript/PixiJs)
* [Lump (LÖVE2D)](https://github.com/sixFingers/lump) (Lua)
* [flump-hx](https://github.com/CrazyFlasher/flump-hx) (HaXe/OpenFL)
