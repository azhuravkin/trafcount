CC = gcc -Wall -O0 -g -ggdb
LIBS = -liptc
DBDIR = "/var/lib/trafcount"
TARGET = trafcount
OBJECTS = trafcount.o database.o

all: $(TARGET)

trafcount: Makefile database.o trafcount.o
	$(CC) -o $(TARGET) $(OBJECTS) $(LIBS)

trafcount.o: Makefile trafcount.c trafcount.h database.h
	$(CC) -c -D'DBDIR=$(DBDIR)' -o trafcount.o trafcount.c

database.o: Makefile database.c database.h trafcount.h
	$(CC) -c -o database.o database.c

clean:
	rm -f $(OBJECTS) $(TARGET)
