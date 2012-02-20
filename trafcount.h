#ifndef TRAFCOUNT_H
#define TRAFCOUNT_H

#define IP_PARTS_NATIVE(n)		\
(unsigned int)((n) >> 24) & 0xFF,	\
(unsigned int)((n) >> 16) & 0xFF,	\
(unsigned int)((n) >> 8)  & 0xFF,	\
(unsigned int)((n) >> 0)  & 0xFF

#define IP_PARTS(n) IP_PARTS_NATIVE(ntohl(n))

#endif
