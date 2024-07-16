# bip3 changelog

## 3.2

* Components now use `dyn-libs` instead of simply `libs`.
* Added `c-info` command-line action.

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
  includes 64-bit code and SSE4.2 being required for release builds.
  Whole-program optimization is now enabled for MSC-like compilers.
* Renamed "optimized" builds to "release" builds
* Support for symbols being hidden by default on non-Windows platforms.
* Separate output and object directories for debug and release builds.
* Removed the ability to change object or output directories of executable and
  library components.
* Use correct object file extension based on the platform. (`.obj` on Windows,
  `.o` otherwise)
