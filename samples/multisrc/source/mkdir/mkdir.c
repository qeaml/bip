#include "mkdir.h"
#include "mkdir_internal.h"

int UniversalMkDir( const char *path )
{
  if( path == 0 || path[0] == 0 )
  {
    return 0;
  }

  return MkDirImpl(path);
}
