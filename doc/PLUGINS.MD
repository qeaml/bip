# Plugins

bip can be extended with your own Python code through the use of **plugins**.

## Anatomy of a plugin

Every plugin is contained within its own directory within the project's source
directory. A plugin's directory must contain a `plug.py` file, which contains
the main interface through which bip will talk with the plugin.

Plugins allow you to integrate just about anything with bip. Because plugins are
written in Python, there is no realistic limit to what you can do.

### Note regarding local and global plugins

Although not currently (v2.1.1) implemented, plugins may be **local** or
**global**.

**Local plugins** are present in the project's source tree.

**Global plugins** are installed system-wide.

Global plugins are highly reusable and reduce the amount of clutter within a
project's source tree.

There is no official bip plugin repository, but a plugin can be automatically
installed using the `add-plug` command. See `bip help add-plug` for more info.

## Plugin interface

### Required

The following functions must be present in `plug.py`.

* `configure(pathes: bip.Pathes, settings: dict[str, str]) -> bool`:
  Prepare the plugin before doing anything else. The pathes are calculated in
  the exact same way as for any other component. These same pathes are used to
  locate the plugin's code. The settings dictionary is simply any properties
  defined within the component that bip could not understand. This is your main
  way of configuring the plugin on a per-component basis.
* `run() -> bool`:
  Execute the plugin. If a `want_run` function is defined (see below) and
  returns `False`, this function will not be called.

### Optional

* `want_run() -> bool`:
  Determines whether the plugin wants to execute. For example, if your plugin
  packs some resources into a single archive, this would return `True` if the
  resources changed or if the resulting archive is missing. If this function is
  not defined, the plugin will always run.
* `clean() -> None`:
  Delete any artifacts that may have been created by this plugin.
* `compile_commands() -> bip.CompileCommands`:
  Calculate entries to be placed within the `compile_commands.json` file. This
  is only relevant in rare scenarios where a C compiler is invoked by a plugin.

## Plugins in the recipe file

A component is declared as a plugin by defining the `plug` property. The value
of this property is used to find where the plugin's code is. The plugin is
located as follows:

```path
<recipe `src` dir>/<component `src` dir>/<`plug` dir>/plug.py
```

Plugins are configurable through properties in the component. See the example
below.

## Example

A simple example is embedding shader source code into a C++ file.

Say we have a plugin called `embed_shader`.

To configure it to take shader source code from `source/shaders` and place it in
C++ source code files in `source/renderer/shaders`.

```toml
[embed_shader]
plug = "plugins/embed_shader"
shader-src = "source/shaders"
shader-out = "source/renderer/shaders"
```

## Stubs

You can copy-paste the below code to quickstart creating a plugin:

```py
"""This is my plugin. Here's what it does."""

import bip

def configure(pathes: bip.Pathes, settings: dict[str, str]) -> bool:
  # Read all the configuration from settings
  return True

def run() -> bool:
  # Do things
  bip.note("Hello, world!")
  return True

def want_run() -> bool:
  # Determine if we want to do things
  return True

def clean() -> None:
  # Remove artifacts
  return

def compile_commands() -> bip.CompileCommands:
  # Return any entries to be added to compile_commands.json
  return []
```
