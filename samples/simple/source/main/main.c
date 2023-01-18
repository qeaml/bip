#include <stdio.h>

extern const char *hello();

int main(int argc, char **argv) {
  printf("Hello, world!\n");
  printf("%s\n", hello());
}
