#include "mkdir_internal.h"
#include <sys/stat.h>
#include <sys/types.h>

int MkDirImpl( const char *path )
{
  mkdir(path, 0777);
}
