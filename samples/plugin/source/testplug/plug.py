import bip

def configure(pathes: bip.Pathes, settings: dict[str, str]) -> bool:
  return True

def run() -> bool:
  bip.note("Hello from testplug!")
  return True
