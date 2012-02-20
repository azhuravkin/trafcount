#ifndef DATABASE_H
#define DATABASE_H

#include <libiptc/libiptc.h>

enum {
    INCOMING,
    OUTGOING
};

struct data {
    char name[IFNAMSIZ];
    u_int64_t in_count;
    u_int64_t out_count;
    u_int64_t in_bytes;
    u_int64_t out_bytes;
};

struct header {
    u_int32_t date;
    int num;
    struct data parts[0];
};

struct collector {
    char name[IFNAMSIZ];
    u_int32_t ip;
    u_int64_t in_count;
    u_int64_t out_count;
    struct collector *next;
};

int update_db(const char *, u_int32_t, const char *, int, u_int64_t);

#endif
