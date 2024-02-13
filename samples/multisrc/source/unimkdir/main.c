#include "mkdir.h"
#include <stdio.h>

int main( int argc, char **argv )
{
  if( argc < 2 )
  {
    fprintf( stderr,
      "Usage: %s <directory name> [directory names...]\n",
      argv[ 0 ] );
    return 1;
  }

  for( int i = 1; i < argc; ++i )
  {
    const char *arg = argv[ i ];
    if(arg[ 0 ] == '-')
    {
      /* We do not parse options, but the user may not know this */
      continue;
    }

    if( !UniversalMkDir( arg ) )
    {
      fprintf( stderr,
        "Could not create directory `%s` :(\n",
        arg );
    }
  }
}
