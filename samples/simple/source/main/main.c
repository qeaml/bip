#include <stdio.h>

extern const char *hello(void);

int main(int argc, char **argv) {
  (void)argc; (void)argv;
  printf("Hello, world!\n");
  printf("%s\n", hello());
}
