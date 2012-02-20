#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <sys/stat.h>
#include "trafcount.h"
#include "database.h"

static struct collector *head = NULL;

static void update_collector(u_int32_t ip, const char *name, u_int64_t count, int direction) {
    struct collector *cur, *prev = NULL;

    for (cur = head; cur; cur = cur->next) {
	if ((cur->ip == ip) && !strcmp(cur->name, name)) {
	    if (direction == INCOMING)
		cur->in_count += count;
	    else
		cur->out_count += count;
	    return;
	}
	prev = cur;
    }

    cur = calloc(1, sizeof(struct collector));
    strcpy(cur->name, name);
    cur->ip = ip;

    if (direction == INCOMING)
	cur->in_count = count;
    else
	cur->out_count = count;

    if (head)
	prev->next = cur;
    else
	head = cur;
}

static int get_counts(u_int32_t date, const char *year) {
    struct iptc_handle *h;
    const char *chain = NULL;
    struct collector *cur, *next;
    char db[128];

    h = iptc_init("filter");

    if (!h)
	return 1;

    for (chain = iptc_first_chain(h); chain; chain = iptc_next_chain(h)) {
	const struct ipt_entry *e;
	char type[IFNAMSIZ];
	int direction;

	if (sscanf(chain, "tc-to-type-%s", type))
	    direction = INCOMING;
	else if (sscanf(chain, "tc-from-type-%s", type))
	    direction = OUTGOING;
	else
	    continue;

	for (e = iptc_first_rule(chain, h); e; e = iptc_next_rule(e, h)) {
	    if (e->ip.src.s_addr && !e->ip.dst.s_addr && strlen(e->ip.outiface) && !strlen(e->ip.iniface)) {
		update_collector(e->ip.src.s_addr, e->ip.outiface, e->counters.bcnt, direction);
		snprintf(db, sizeof(db), "%s/%s/%u.%u.%u.%u.type", DBDIR, year, IP_PARTS(e->ip.src.s_addr));
		update_db(db, date, type, direction, e->counters.bcnt);
	    } else if (!e->ip.src.s_addr && e->ip.dst.s_addr && !strlen(e->ip.outiface) && strlen(e->ip.iniface)) {
		update_collector(e->ip.dst.s_addr, e->ip.iniface, e->counters.bcnt, direction);
		snprintf(db, sizeof(db), "%s/%s/%u.%u.%u.%u.type", DBDIR, year, IP_PARTS(e->ip.dst.s_addr));
		update_db(db, date, type, direction, e->counters.bcnt);
	    }
	}
    }

    iptc_free(h);

    for (cur = head; cur; cur = next) {
	next = cur->next;
	snprintf(db, sizeof(db), "%s/%s/%u.%u.%u.%u.intf", DBDIR, year, IP_PARTS(cur->ip));
	update_db(db, date, cur->name, INCOMING, cur->in_count);
	update_db(db, date, cur->name, OUTGOING, cur->out_count);
	free(cur);
    }

    return 0;
}

int main(void) {
    time_t t;
    struct stat st;
    char date[16];
    char year[8];
    char path[128];

    time(&t);
    /* Формируем текущую дату в формате YYYYMMDD */
    if ((strftime(date, sizeof(date), "%Y%m%d", localtime(&t))) == 0) {
	fprintf(stderr, "Error in strftime()\n");
	return 1;
    }

    /* Формируем текущий год YYYY */
    if ((strftime(year, sizeof(year), "%Y", localtime(&t))) == 0) {
	fprintf(stderr, "Error in strftime()\n");
	return 1;
    }

    snprintf(path, sizeof(path), "%s/%s", DBDIR, year);

    if (stat(path, &st) == EOF)
	mkdir(path, 0755);

    get_counts(atoi(date), year);

    return 0;
}
