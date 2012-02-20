CC = gcc -Wall -O0 -g -ggdb
LIBS = -liptc
DBDIR = "/var/lib/trafcount"

all: trafcount

trafcount: Makefile trafcount.c
	$(CC) -D'DBDIR=$(DBDIR)' -o trafcount trafcount.c $(LIBS)

clean:
	rm -f trafcount
