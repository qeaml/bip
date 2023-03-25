import bip.build

def clean(bld: bip.build.Info) -> bool:
  """ Clean up any files created by previous builds.
      Return False on failure and use bld.log to report the error. """

  return True

def should_build(bld: bip.build.Info) -> bool:
  """ Check if the previous build results are up-to-date. """

  return True

def build(bld: bip.build.Info) -> bool:
  """ Build. This is only called if should_build returned True.
      Return False on failure and use bld.log to report the error. """

  bld.log.note("Hello from testplug!")
  return True
