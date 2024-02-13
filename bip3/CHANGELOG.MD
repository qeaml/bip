# bip3 changelog

## 3.0

This is the first fully functional version of bip3. Below is a list of how it
differs from bip2.

* More granular control over language configuration. Language-level
  configuration was abstracted upon and can now be defined per-component.
* Better separation of component kinds. Plugin components no longer suffer from
  limitations with `src`, `obj`, `out` keys in their definitions.
* Better support for different C compilers. Bip can now automatically pick a
  compiler if one isn't specified by the recipe or component. It will only pick
  compilers which are present in the current environment.
* Support for defining C/C++ preprocessor macros.
* Additional compiler command line flags passed for more consistent behavior
  across different compilers (most notably MSC and GNU-like compilers). This
  includes 64-bit code and SSE4.2 being required for optimized builds.
  Whole-program optimization is now enabled for MSC-like compilers.
