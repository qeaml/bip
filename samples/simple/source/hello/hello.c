#if defined(_WIN32)
  #define LIBRARY_API __declspec(dllexport)
#else
  #define LIBRARY_API
#endif

LIBRARY_API const char *hello(void) {
  return "Hello, foobar!";
}
