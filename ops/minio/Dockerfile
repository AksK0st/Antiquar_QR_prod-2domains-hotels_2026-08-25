FROM quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z AS client
FROM quay.io/minio/minio:RELEASE.2025-10-15T17-29-55Z
COPY --from=client /usr/bin/mc /usr/bin/mc
RUN chmod 0755 /usr/bin/mc
