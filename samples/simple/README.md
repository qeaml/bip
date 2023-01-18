# Simple Sample

This is a simple project configured with a bip recipe.

The recipe will build the component `hello` as a shared library (in case of
MSVC that would result in `hello.dll`) and then build `main` as an executable
linking against `hello` (`main.exe` and `hello.lib` respectively).

## Recipe explanation

The `build` section of the recipe defines values that apply to every component.

This includes:
* `cc` - the C/C++ compiler to use. This sample is configured for MSVC as it's
         the only compiler which reliably works with bip. You may change this to
         `"clang"` to try compiling with clang instead.
* `src` - the main source directory. All components will be located in sub-
          directories of this directory.
* `out` - the main binary output directory. Shared libraries and executables end
          up here.
* `obj` - the object file output directory. Compiled object files end up here.

Every other section of the file defines a component. Let's look at the `hello`
component:
* `lib` - defines this component as a shared library. The value will be used as
          the name of the library, which is usually the same as the name of the
          component but does not have to be.

And then the `main` component:
* `exe` - defines this component as an executable. Alike `lib` this contains
          the executable's name and may differ from the component name.
* `libs` - the static librariess to link this component against. Although in
           this example we only provide this for the executable, you can
           provide this list for shared library components to link against them.
