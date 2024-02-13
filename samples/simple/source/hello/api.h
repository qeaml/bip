#ifdef _WIN32
  #if HELLO_BUILD
    #define HELLO_API __declspec(dllexport)
  #else
    #define HELLO_API __declspec(dllimport)
  #endif
#else
  #if HELLO_BUILD
    #define HELLO_API __attribute__((visibility("default")))
  #else
    #define HELLO_API extern
  #endif
#endif
