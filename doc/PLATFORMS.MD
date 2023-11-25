# Platforms & Platform Restrictions

## Supported Platforms

bip currently distinguishes between 3 major platforms:

* Windows
* Generic Linux
* Mac OS

## Platform Restrictions

It is generally encouraged to write code in a platform-independent way, but
that may not always be possible.

In such cases, you may use a component's `platform` key to restrict which
platforms it is built on.

For example, to restrict a component to only build on Windows:

```toml
[my_component]
# ... other properties
platform = "win"
```

The value of the platform key is case insensitive, and can be any of the
following values:

* Windows: `win`, `win32`, `windows`
* Linuxes: `linux`, `unix`
* Mac OS: `osx`, `mac`, `darwin`, `macosx`

In case the platform restriction is not recognized, you will receive a warning
and the component will not be built.

## Example

The libraries that you must link against to interact with OpenGL are different
for different platforms.

On Windows, you must link against `opengl32`. On Linuxes, you must link against
`GL` instead.

```toml
[gl_win]
platform = "win"
# ... other properties
libs = [
  # ... other libs
  "opengl32"
]

[gl_linux]
platform = "linux"
# ... other properties
libs = [
  # ... other libs
  "GL"
]
```
