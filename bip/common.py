from dataclasses import dataclass

@dataclass
class Log:
  is_verbose: bool

  def verbose(self, msg: str) -> None:
    if self.is_verbose:
      print(msg)

  def note(self, msg: str) -> None:
    print("\x1b[1m" + msg + "\x1b[22m")

  def warn(self, msg: str) -> None:
    print("\x1b[33m" + msg + "\x1b[39m")

  def err(self, msg: str) -> None:
    print("\x1b[1m\x1b[31m" + msg + "\x1b[39m\x1b[22m")
