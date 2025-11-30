# PESU Scrape

This is a simple python script to scrape the pesu website for course details and store it in a database.

## Docker Support

You can run the application using Docker.

### Build the container
```bash
docker build -t pesu-scrape .
```

### Run the container
```bash
docker run -p 5000:5000 pesu-scrape
```

The application will be available at http://localhost:5000.
