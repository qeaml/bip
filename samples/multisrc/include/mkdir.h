#ifdef _WIN32
  #if MKDIR_BUILD
    #define MKDIR_API __declspec(dllexport)
  #else
    #define MKDIR_API __declspec(dllimport)
  #endif
#else
  #if MKDIR_BUILD
    #define MKDIR_API __attribute__((visibility("default")))
  #else
    #define MKDIR_API extern
  #endif
#endif

MKDIR_API int UniversalMkDir(const char *path);
