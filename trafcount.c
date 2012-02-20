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
	int date;
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

int search(FILE *, int);
int get_counts(int, char *, char *, char *);
void free_interfaces(struct interface *);
int update_db(char *, int, unsigned long, unsigned long);

void free_interfaces(struct interface *head) {
	struct interface *cur, *next;

	for (cur = head; cur; cur = next) {
		next = cur->next;
		free(cur);
	}
}

int search(FILE *database, int date) {
	/* Ищем нужную позицию в db */
	int i;
	struct record rec;
	int dates[RECORDS];

	memset(&rec, 0, sizeof(struct record));

	for (i = 0; ((i < RECORDS) && (!feof(database))); i++) {
		fread(&rec, sizeof(struct record), 1, database);
		dates[i] = rec.date;
	}

	/* Если db полностью пустая, переходим в начало файла */
	if (dates[0] == 0) {
		rewind(database);
		return 0;
	}

	/* Если в db есть нужная запись, переходим на эту позицию и возвращаем 1, чтобы считать запись */
	for (i = 0; i < RECORDS; i++)
		if (dates[i] == date) {
			fseek(database, sizeof(struct record) * i, SEEK_SET);
			return 1;
		}

	/* Если дата в последующей записи меньше чем в предыдущей, переходим на позицию последующей */
	for (i = 1; i < RECORDS; i++)
		if (dates[i] < dates[i - 1]) {
			fseek(database, sizeof(struct record) * i, SEEK_SET);
			return 0;
		}

	/* Либо переходим в начало файла */
	rewind(database);
	return 0;
}

int update_db(char *db, int date, unsigned long in_count, unsigned long out_count) {
	FILE *fp;
	struct record cur;
	int i;

	memset(&cur, 0, sizeof(struct record));

	/* Если файл открылся на обновление - обновляем данные */
	if ((fp = fopen(db, "rb+"))) {
		if (search(fp, date)) {
			/* Читаем одну запись с текущей позиции */
			fread(&cur, sizeof(struct record), 1, fp);
			/* И переходим на её начало */
			fseek(fp, sizeof(struct record) * -1, SEEK_CUR);
		}

		/* Записываем обновлённые данные */
		cur.date = date;
		if (cur.in_count && (cur.in_count < in_count))
			cur.in_bytes += in_count - cur.in_count;
		if (cur.out_count && (cur.out_count < out_count))
			cur.out_bytes += out_count - cur.out_count;
		cur.in_count = in_count;
		cur.out_count = out_count;

		fwrite(&cur, sizeof(struct record), 1, fp);

	/* Если файл открылся на запись, инициализируем его нулями */
	} else if ((fp = fopen(db, "wb"))) {
		for (i = 0; i < RECORDS; i++)
			fwrite(&cur, sizeof(struct record), 1, fp);
	/* Файл не открылся ни на обновление ни на запись */
	} else {
		fprintf(stderr, "Error opening db file: %s\n", db);
		return 1;
	}

	fclose(fp);

	return 0;
}

int get_counts(int date, char *host, char *comm, char *intfs) {
	char *ifname;
	char db[128];
	short oper_status = 0;
	unsigned long in_count = 0;
	unsigned long out_count = 0;
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
	session.community = (u_char *) comm;
	session.community_len = strlen(comm);

	/* Открываем snmp сессию */
	if ((ss = snmp_open(&session)) == NULL) {
		fprintf(stderr, "Error in snmp_open().\n");
		return 1;
	}

	snprintf(objid, MAX_OID_LEN, "%s.%u", BASE_OID, INDEXES);
	read_objid(objid, index_oid, &index_oid_length);

	memmove(var_oid, index_oid, index_oid_length * sizeof(oid));
	var_oid_length = index_oid_length;

	/* Получаем в цикле список всех интерфейсов и их индексов и сохряняем их в списке */
	while (running) {
		pdu = snmp_pdu_create(SNMP_MSG_GETNEXT);
		snmp_add_null_var(pdu, var_oid, var_oid_length);

		status = snmp_synch_response(ss, pdu, &response);

		if (status == STAT_SUCCESS && response->errstat == SNMP_ERR_NOERROR) {
			for (var = response->variables; var; var = var->next_variable) {
				if (!memcmp(var->name, index_oid, index_oid_length * sizeof(oid))) {
					if ((cur = malloc(sizeof(struct interface))) == NULL) {
						fprintf(stderr, "Error in malloc().\n");
						return 1;
					}
					cur->index = var->name[index_oid_length];
					snprintf(cur->name, var->val_len + 1, (char *) var->val.string);
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

	/* Для каждого интерфейса, для которого нужно считать трафик */
	for (ifname = strtok(intfs, ","); ifname; ifname = strtok(NULL, ",")) {
		/* Для каждого интерфейса в списке */
		for (running = 1, cur = prev; running && cur; cur = cur->next) {
			/* Если имена интерфейсов совпадают */
			if (!strcmp(ifname, cur->name)) {
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
					/* Для каждого полученного значения */
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
						}
					}
					/* Если интерфейс в состоянии UP */
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
	}

	free_interfaces(prev);
	return 0;
}

int main(int argc, char **argv) {
	int i;
	time_t t;
	struct tm *tm;
	int date;
	char date_str[16];
	char *community;
	char *interfaces;
	char *at;
	char arg[128];

	if (argc < 2) {
		fprintf(stderr, "Usage: %s host[:community]@ifname1[,ifname2,...] ...\n", argv[0]);
		return 1;
	}

	/* Формируем текущую дату в формате YYYYMMDD */
	t = time(NULL);
	tm = localtime(&t);
	if ((strftime(date_str, sizeof(date_str), "%Y%m%d", tm)) == 0) {
		fprintf(stderr, "Error in strftime()\n");
		return 1;
	}

	date = atoi(date_str);

	for (i = 1; i < argc; i++) {
		snprintf(arg, sizeof(arg), argv[i]);

		if ((at = strchr(arg, '@'))) {
			/* Если список интерфейсов пустой */
			if (*(interfaces = at + 1) == '\0')
				continue;
			*at = '\0';
		} else
			continue;

		if ((community = strchr(arg, ':'))) {
			*community = '\0';
			community++;
		}

		get_counts(date, arg, community ? community : "public", interfaces);
	}

	return 0;
}
