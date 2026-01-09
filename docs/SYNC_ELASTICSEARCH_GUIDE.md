# Elasticsearch Field Sync Guide

This guide explains how to sync updated fields (NER entities, HDBSCAN topics) from your local Elasticsearch to GCP VM Elasticsearch.

## Quick Start

```bash
# Sync both NER entities and HDBSCAN topics
python scripts/sync_updated_fields.py --remote-host http://YOUR_GCP_VM_IP:9200

# Sync only NER entities
python scripts/sync_updated_fields.py --remote-host http://YOUR_GCP_VM_IP:9200 --no-topics

# Sync only HDBSCAN topics
python scripts/sync_updated_fields.py --remote-host http://YOUR_GCP_VM_IP:9200 --no-ner

# Use larger batch size for faster sync
python scripts/sync_updated_fields.py --remote-host http://YOUR_GCP_VM_IP:9200 --batch-size 1000

# Verify sync after completion
python scripts/sync_updated_fields.py --remote-host http://YOUR_GCP_VM_IP:9200 --verify
```

## Prerequisites

1. **Network Access**: Your local machine must be able to reach the GCP VM Elasticsearch
2. **Firewall**: Port 9200 must be open on GCP VM firewall
3. **Elasticsearch Running**: Both local and remote Elasticsearch must be running

## Setup GCP VM Firewall

```bash
# Get your local IP address
curl ifconfig.me

# Create firewall rule to allow your IP
gcloud compute firewall-rules create allow-es-sync \
  --allow tcp:9200 \
  --source-ranges YOUR_IP_ADDRESS/32 \
  --target-tags elasticsearch \
  --description "Allow Elasticsearch sync from local machine"
```

## Get GCP VM IP Address

```bash
# List all VMs
gcloud compute instances list

# Get specific VM IP
gcloud compute instances describe tbmm-elasticsearch \
  --zone=europe-west3-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

## Usage Examples

### Example 1: Sync Everything

```bash
export REMOTE_ES_HOST="http://34.159.123.45:9200"
python scripts/sync_updated_fields.py --remote-host $REMOTE_ES_HOST
```

### Example 2: Incremental Sync (Only Updated Fields)

```bash
# Sync only documents that have NER entities or HDBSCAN topics
python scripts/sync_updated_fields.py \
  --remote-host http://34.159.123.45:9200 \
  --batch-size 1000
```

### Example 3: Sync Only NER Entities

```bash
python scripts/sync_updated_fields.py \
  --remote-host http://34.159.123.45:9200 \
  --no-topics
```

### Example 4: Sync Only HDBSCAN Topics

```bash
python scripts/sync_updated_fields.py \
  --remote-host http://34.159.123.45:9200 \
  --no-ner
```

## What Gets Synced

The script syncs these fields from local to remote:

1. **NER Entities** (`ner_entities`):
   - Entity names
   - Entity types (PER, LOC, ORG)
   - Frequencies
   - Confidence scores
   - Wikipedia URLs (if available)

2. **HDBSCAN Topics**:
   - `hdbscan_topic_id`: Topic ID number
   - `hdbscan_topic_label`: Topic label/name

## How It Works

1. **Connects** to both local and remote Elasticsearch
2. **Finds** documents that have NER entities or HDBSCAN topics
3. **Extracts** only the fields that need updating
4. **Updates** remote documents in batches (default: 500 per batch)
5. **Refreshes** remote index to make updates visible
6. **Verifies** sync (if `--verify` flag is used)

## Performance

- **Batch Size**: Default 500, can be increased to 1000-2000 for faster sync
- **Network Speed**: Depends on your connection to GCP VM
- **Estimated Time**: 
  - 27,662 documents with 500 batch size: ~5-10 minutes
  - With 1000 batch size: ~3-5 minutes

## Troubleshooting

### Connection Failed

```
❌ Failed to connect to REMOTE Elasticsearch
```

**Solutions:**
1. Check GCP VM is running: `gcloud compute instances list`
2. Check firewall rules: `gcloud compute firewall-rules list`
3. Test connectivity: `curl http://YOUR_GCP_VM_IP:9200`
4. Check Elasticsearch is running on VM: SSH and run `sudo systemctl status elasticsearch`

### No Documents Found

```
⚠️  No documents found with the specified fields
```

**Solutions:**
1. Verify local ES has the fields: Check with `curl http://localhost:9200/parliament_speeches/_search?q=ner_entities`
2. Check field names match exactly
3. Run NER extraction or topic analysis first

### Sync Errors

```
⚠️  Error: [error details]
```

**Solutions:**
1. Check remote index exists: `curl http://YOUR_GCP_VM_IP:9200/parliament_speeches`
2. Check remote index mapping includes the fields
3. Reduce batch size: `--batch-size 100`
4. Check network stability

## Alternative: SSH Tunnel Method

If direct connection doesn't work, use SSH tunnel:

```bash
# Terminal 1: Create SSH tunnel
ssh -i ~/.ssh/your-key \
    -L 9201:localhost:9200 \
    -N -f \
    your-user@YOUR_GCP_VM_IP

# Terminal 2: Run sync using tunnel
python scripts/sync_updated_fields.py \
  --remote-host http://localhost:9201
```

## Verification

After sync, verify the data:

```bash
# Check NER entities count
curl -X POST "http://YOUR_GCP_VM_IP:9200/parliament_speeches/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"nested": {"path": "ner_entities", "query": {"exists": {"field": "ner_entities.entity"}}}}, "size": 0}'

# Check HDBSCAN topics count
curl -X POST "http://YOUR_GCP_VM_IP:9200/parliament_speeches/_search" \
  -H 'Content-Type: application/json' \
  -d '{"query": {"exists": {"field": "hdbscan_topic_id"}}, "size": 0}'
```

## Script Options

```
--local-host          Local ES host (default: http://localhost:9200)
--remote-host         Remote ES host (REQUIRED: GCP VM IP)
--index               Index name (default: parliament_speeches)
--batch-size          Batch size (default: 500)
--sync-ner            Sync NER entities (default: True)
--sync-topics         Sync HDBSCAN topics (default: True)
--no-ner              Skip NER entities sync
--no-topics           Skip HDBSCAN topics sync
--verify              Verify sync after completion
```

## Environment Variables

You can also use environment variables:

```bash
export LOCAL_ES_HOST="http://localhost:9200"
export REMOTE_ES_HOST="http://34.159.123.45:9200"
export ELASTICSEARCH_INDEX="parliament_speeches"

python scripts/sync_updated_fields.py
```

## Best Practices

1. **Test First**: Run with `--verify` flag first time
2. **Backup**: Consider backing up remote ES before sync
3. **Incremental**: Use incremental sync for regular updates
4. **Monitor**: Watch for errors during sync
5. **Network**: Use stable network connection
6. **Batch Size**: Adjust based on network speed and VM resources

## Next Steps

After syncing:
1. Verify data in remote ES
2. Update API configuration to use remote ES
3. Test API endpoints with synced data
4. Monitor for any issues

