# bip3

**b**uild **i**t **p**lease is a more complex version of [qcbs][qcbs].

## Main difference between bip and qcbs

qcbs is very much usable for smaller projects, like individual CLI tools or
prototypes. It does not require you to think deeply about the final architecture
but comes at a cost of only being able to build a single executable.

bip expands qcbs' functionalities via components. Each component can be a shared
library or an executable. A component's source is contained within a directory
inside whatever is currently defined as the main source directory. For example,
the component `mathutil` would be located in `source/mathutil` if `source` is
the main source folder.

bip also uses TOML for it's recipes because YAML.

## Examples

To see a bip in action, you can check out the [`simple`][simplesample] sample
project.

[qcbs]: https://github.com/qeaml/bs
[simplesample]: samples/simple
