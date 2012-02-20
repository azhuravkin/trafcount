#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <net-snmp/net-snmp-config.h>
#include <net-snmp/net-snmp-includes.h>

#define DBDIR		"/var/lib/trafcount"
#define RECORDS		(365 * 1)
#define BASE_OID	".1.3.6.1.2.1.2.2.1"
#define INDEXES		2
#define STATUS		7
#define IN_OCTETS	10
#define OUT_OCTETS	16

struct record {
	unsigned date;
	unsigned long in_count;
	unsigned long out_count;
	unsigned long long in_bytes;
	unsigned long long out_bytes;
};

struct interface {
	unsigned index;
	char name[32];
	struct interface *next;
};

int get_counts(unsigned, char *, char *, char *);
int update_db(char *, unsigned, unsigned long, unsigned long);
int search(FILE *fp, unsigned int date);
void free_interfaces(struct interface *);

void free_interfaces(struct interface *head) {
	struct interface *cur, *next;

	for (cur = head; cur; cur = next) {
		next = cur->next;
		free(cur);
	}
}

int search(FILE *database, unsigned date) {
	/* Ищем нужную позицию в db */
	int i;
	int fill = 0;
	struct record rec;
	unsigned dates[RECORDS];

	memset(&rec, 0, sizeof(struct record));

	for (i = 0; ((i < RECORDS) && (!feof(database))); i++) {
		fread(&rec, sizeof(struct record), 1, database);
		if (rec.date) fill = 1;
		dates[i] = rec.date;
	}

	/* Если db полностью пустая, переходим в начало файла */
	if (!fill) {
		rewind(database);
		return 0;
	}

	/* Если в db есть нужная запись, переходим на эту позицию и возвращаем 1, чтобы считать запись */
	for (i = 0; i < RECORDS; i++)
		if (dates[i] == date) {
			fseek(database, sizeof(struct record) * i, SEEK_SET);
			return 1;
		}

	/* Если дата в текущей записи меньше чем в предыдущей, переходим на позицию текущей */
	for (i = 1; i < RECORDS; i++)
		if (dates[i] < dates[i - 1]) {
			fseek(database, sizeof(struct record) * i, SEEK_SET);
			return 0;
		}

	/* Либо переходим в начало файла */
	rewind(database);
	return 0;
}

int update_db(char *db, unsigned u_date, unsigned long in_count, unsigned long out_count) {
	FILE *fp;
	struct record cur_record;
	int i;
	
	memset(&cur_record, 0, sizeof(struct record));

	if (fp = fopen(db, "rb+")) {
		/* Update db */
		if (search(fp, u_date)) {
			fread(&cur_record, sizeof(struct record), 1, fp);
			/* Back to begin this record */
			fseek(fp, sizeof(struct record) * -1, SEEK_CUR);
		}

		cur_record.date = u_date;
		if (cur_record.in_count && (cur_record.in_count < in_count))
			cur_record.in_bytes += in_count - cur_record.in_count;
		if (cur_record.out_count && (cur_record.out_count < out_count))
			cur_record.out_bytes += out_count - cur_record.out_count;
		cur_record.in_count = in_count;
		cur_record.out_count = out_count;

		fwrite(&cur_record, sizeof(struct record), 1, fp);

	} else if (fp = fopen(db, "wb")) {
		/* Initialize db */
		for (i = 0; i < RECORDS; i++)
			fwrite(&cur_record, sizeof(struct record), 1, fp);
	} else {
		fprintf(stderr, "Error opening db file: %s\n", db);
		return 1;
	}

	fclose(fp);

	return 0;
}

int get_counts(unsigned date, char *host, char *comm, char *intfs) {
	char *ifname;
	char db[128];
	short oper_status;
	unsigned long in_count, out_count;
	struct snmp_session session, *ss;
	struct snmp_pdu *pdu, *response;
	struct variable_list *var;
	int status, running = 1;
	oid index_oid[MAX_OID_LEN];
	oid var_oid[MAX_OID_LEN];
	size_t index_oid_length = MAX_OID_LEN;
	size_t var_oid_length = MAX_OID_LEN;
	char objid[MAX_OID_LEN];
	struct interface *cur, *prev = NULL;

	snprintf(db, sizeof(db), "%s/%s", DBDIR, host);
	mkdir(db, 0755);

	snmp_sess_init(&session);
	session.peername = host;
	session.version = SNMP_VERSION_1;
	session.community = comm ? comm : "public";
	session.community_len = strlen(session.community);

	/* Open the session */
	if ((ss = snmp_open(&session)) == NULL) {
		fprintf(stderr, "Error in snmp_open().\n");
		return 1;
	}

	/* Read indexes */
	snprintf(objid, MAX_OID_LEN, "%s.%u", BASE_OID, INDEXES);
	read_objid(objid, index_oid, &index_oid_length);

	memmove(var_oid, index_oid, index_oid_length * sizeof(oid));
	var_oid_length = index_oid_length;

	while (running) {
		pdu = snmp_pdu_create(SNMP_MSG_GETNEXT);
		snmp_add_null_var(pdu, var_oid, var_oid_length);

		status = snmp_synch_response(ss, pdu, &response);

		if (status == STAT_SUCCESS && response->errstat == SNMP_ERR_NOERROR) {
			for (var = response->variables; var; var = var->next_variable) {
				if (!memcmp(var->name, index_oid, index_oid_length * sizeof(oid))) {
					cur = malloc(sizeof(struct interface));
					cur->index = var->name[index_oid_length];
					snprintf(cur->name, var->val_len + 1, var->val.string);
					cur->next = prev;
					prev = cur;
					
					memmove(var_oid, var->name, var->name_length * sizeof(oid));
					var_oid_length = var->name_length;
				} else
					running = 0;
			}
		} else
			running = 0;
	}

	ifname = strtok(intfs, ",");

	do {
		for (running = 1, cur = prev; cur && running; cur = cur->next) {
			if (!strcmp(cur->name, ifname)) {
				pdu = snmp_pdu_create(SNMP_MSG_GET);

				snprintf(objid, sizeof(objid), "%s.%u.%u", BASE_OID, STATUS, cur->index);
				read_objid(objid, var_oid, &var_oid_length);
				snmp_add_null_var(pdu, var_oid, var_oid_length);

				snprintf(objid, sizeof(objid), "%s.%u.%u", BASE_OID, IN_OCTETS, cur->index);
				read_objid(objid, var_oid, &var_oid_length);
				snmp_add_null_var(pdu, var_oid, var_oid_length);

				snprintf(objid, sizeof(objid), "%s.%u.%u", BASE_OID, OUT_OCTETS, cur->index);
				read_objid(objid, var_oid, &var_oid_length);
				snmp_add_null_var(pdu, var_oid, var_oid_length);

				status = snmp_synch_response(ss, pdu, &response);

				if (status == STAT_SUCCESS && response->errstat == SNMP_ERR_NOERROR) {
					for (var = response->variables; var; var = var->next_variable) {
						switch (var->name[9]) {
							case STATUS:
								oper_status = *var->val.integer;
								break;
							case IN_OCTETS:
								in_count = *var->val.integer;
								break;
							case OUT_OCTETS:
								out_count = *var->val.integer;
								break;
							default:
								break;
						}
					}
					if (oper_status == 1) {
						snprintf(db, sizeof(db), "%s/%s/%s.db", DBDIR, host, ifname);
						update_db(db, date, in_count, out_count);
						running = 0;
					}
				} else {
					fprintf(stderr, "Error in snmp_synch_response()\n");
					snmp_free_pdu(response);
					snmp_close(ss);
					free_interfaces(prev);
					return 1;
				}

				snmp_free_pdu(response);
			}
		}
	} while (ifname = strtok(NULL, ","));

	free_interfaces(prev);
	return 0;
}

int main(int argc, char **argv) {
	int i;
	time_t t;
	struct tm *tm;
	char date[16];
	unsigned u_date;
	char *community;
	char *interfaces;
	char *at;

	if (argc < 2) {
		fprintf(stderr, "Usage: %s host[:community]@ifname1[,ifname2 ...] ...\n", argv[0]);
		exit(1);
	}

	t = time(NULL);
	tm = localtime(&t);
	if ((strftime(date, sizeof(date), "%Y%m%d", tm)) == 0) {
		fprintf(stderr, "Error in strftime()\n");
		exit(1);
	}

	init_snmp("trafcount");
	u_date = (unsigned) strtol(date, NULL, 10);

	for (i = 1; i < argc; i++) {
		if (at = strchr(argv[i], '@')) {
			if (*(interfaces = at + 1) == '\0')
				continue;
			*at = '\0';
		} else
			continue;

		if (community = strchr(argv[i], ':')) {
			*community = '\0';
			community++;
		}

		if (get_counts(u_date, argv[i], community, interfaces))
			continue;
	}

	return 0;
}
