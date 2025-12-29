# A Dockerfile for the Go version of the webapp, intended for Google Cloud Run
# based on:
# https://github.com/GoogleContainerTools/distroless/blob/main/examples/go/Dockerfile

# Stage 1: Build the Go application
FROM golang:1.22-alpine AS build
WORKDIR /app
COPY . .
RUN go mod download
RUN CGO_ENABLED=0 go build -o tess_dv_fast_server .

#
# Stage 2: Create a minimal final image
FROM gcr.io/distroless/static-debian12
WORKDIR /app
COPY --from=build /app/tess_dv_fast_server .
# the sqlite db files directory
COPY data data
# build SHA
COPY build.txt build.txt

# starting the main process
CMD ["./tess_dv_fast_server"]
