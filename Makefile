CC = gcc -Wall -O2 -g -ggdb
LIBS = -lsnmp
prefix = /usr/local
sbindir = ${prefix}/sbin

all: trafcount

trafcount: Makefile trafcount.c
	$(CC) $(LIBS) -o trafcount trafcount.c

install: trafcount
	install -o root -s trafcount $(sbindir)

clean:
	rm -f trafcount
