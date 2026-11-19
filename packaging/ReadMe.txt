LibreSprite for AROS
====================

LibreSprite is a pixel art editor for sprites and animations. It has layers,
animation frames with onion skin, palettes and a tiled mode for repeating
patterns, and it exports PNG, GIF and sprite sheets.

This version is built from the LibreSprite development branch of 14 November
2026, which uses SDL 3. It runs on:

- x86_64 ABIv11 distributions (tested on AROS One 1.3)
- mainline AROS x86_64
- mainline AROS on the Raspberry Pi (tested in QEMU only)


Starting
--------

Double-click the LibreSprite icon. A picture whose icon has LibreSprite as
its default tool opens with a double-click too, and you can drop picture
icons on the LibreSprite window.

From a Shell, in the LibreSprite drawer:

    LibreSprite
    LibreSprite Work:Pictures/hero.png

LibreSprite asks AROS for the stack it needs, so you do not have to set one.
Keep the data drawer next to the program.


Working with AROS
-----------------

- The menus are in the window's menu bar: hold the right mouse button over
  the title bar of the window or of the screen. In the drawing area the right
  mouse button paints with the background colour, as in LibreSprite on other
  systems.
- Every command with a Ctrl+letter shortcut also works with Amiga+letter.
- The iconify gadget turns the window into an icon on the Workbench.
  Double-click the icon to get the window back.
- Copy and Paste work with other programs. Pictures go through the clipboard
  as IFF ILBM, so you can paste a screenshot from AROS Capture or view a
  copied picture in MultiView. Text uses the system character set.
  Transparency survives only when you copy and paste inside LibreSprite.
- File names may contain national characters that exist in the system
  character set (Locale preferences). If a name has a character that set
  cannot hold, LibreSprite does not save the file and tells you why.
- On Polish and other national keyboards, the right Alt key (AltGr) types
  its characters in text fields instead of acting as an Alt shortcut.

Settings, palettes and the backups used for crash recovery are in
ENVARC:LibreSprite.


Drawing with OpenGL
-------------------

The GUI_RENDERER tool type in the LibreSprite icon decides how the window is
drawn:

    GUI_RENDERER=AUTO   OpenGL when gl.library is installed (default)
    GUI_RENDERER=GPU    always OpenGL
    GUI_RENDERER=CPU    without OpenGL

With AUTO you can also turn OpenGL off with the "GPU acceleration" option
in Edit > Preferences. Change the tool type in the icon's Information window.

If the window shows a wrong or damaged picture, or is not redrawn after you
move or resize it, use GUI_RENDERER=CPU. CPU mode does not use OpenGL at
all.


Known limitations
-----------------

- fetch() and the HTTP server are not available to scripts.
- The window's menu bar holds one level of submenus. Commands that sit
  deeper are reached through their keyboard shortcuts.
- The file system functions for scripts handle ASCII file names only.
- Known issue: with OpenGL, resizing the window very fast for a long time
  can leave LibreSprite unresponsive. GUI_RENDERER=CPU avoids it. Please
  report it if you see it.
- Most testing was done in QEMU. Reports from real computers are welcome.

Report problems at:
https://github.com/tomaszstaniak/aros-libresprite/issues


Licence
-------

LibreSprite is free software under the GNU General Public License,
version 2 (LICENSE.txt). Licenses/NOTICES.txt lists the libraries it
includes and their licences.

LibreSprite: https://libresprite.github.io
AROS port: https://github.com/tomaszstaniak/aros-libresprite
