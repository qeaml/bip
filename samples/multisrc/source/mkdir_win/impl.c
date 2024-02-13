#include "mkdir_internal.h"
#include <Windows.h>

int MkDirImpl( const char *path )
{
  return CreateDirectoryA( path, NULL );
}
