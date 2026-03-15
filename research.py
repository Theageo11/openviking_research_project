import openviking as ov
import time

# Initialize OpenViking client with data directory
client = ov.SyncOpenViking(path="./data")

try:
    # Initialize the client
    print("Initializing OpenViking client...")
    client.initialize()

    # Add resource (supports URL, file, or directory)
    print("Adding resource...")
    add_result = client.add_resource(
        path="/Users/hongyizhang/AI-companian"
    )
    root_uri = add_result['root_uri']
    print(f"Resource added with URI: {root_uri}\n")

    # Explore the resource tree structure
    print("Exploring resource tree structure...")
    ls_result = client.ls(root_uri)
    print(f"Directory structure:\n{ls_result}\n")

    # Use glob to find markdown files
    print("Finding markdown files...")
    glob_result = client.glob(pattern="**/*.md", uri=root_uri)
    if glob_result['matches']:
        content = client.read(glob_result['matches'][0])
        print(f"Content preview: {content[:200]}...\n")

    # Wait for semantic processing to complete
    print("Waiting for semantic processing (this may take a while)...")
    max_wait_time = 120  # 2 minutes timeout
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        try:
            client.wait_processed()
            print("Semantic processing completed!")
            break
        except RuntimeError as e:
            if "500" in str(e) or "InternalServiceError" in str(e):
                elapsed = time.time() - start_time
                print(f"Service temporarily unavailable (Error 500). Retrying... ({elapsed:.1f}s)")
                time.sleep(5)
            else:
                raise

    # Get abstract and overview of the resource
    print("\nGenerating abstract and overview...")
    abstract = client.abstract(root_uri)
    overview = client.overview(root_uri)
    print(f"Abstract:\n{abstract}\n\nOverview:\n{overview}\n")

    # Perform semantic search
    print("Performing semantic search...")
    results = client.find("怎么生成数据集？", target_uri=root_uri)
    print("Search results:")
    for r in results.resources:
        print(f"  {r.uri} (score: {r.score:.4f})")

    # Close the client
    client.close()
    print("\nClient closed successfully!")

except Exception as e:
    print(f"Unexpected error: {e}")
