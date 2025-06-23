# EG4 Inverter Configuration

## Primary Inverter Details
- **IP Address**: 172.16.107.129
- **Port**: 8000
- **Protocol**: IoTOS
- **Username**: admin
- **Password**: admin
- **Model**: EG4 18kPV

## Connection Notes
- The inverter has intermittent connectivity issues
- Connection may be up and down
- System is configured with automatic retry logic
- Increased timeout values to handle connectivity issues

## Configuration Locations
1. **Main Config**: `config/config.yaml`
2. **Environment Variables**: `.env`
3. **Docker Config**: `docker/config/config.yaml`

## Troubleshooting
If connection fails:
1. Wait a moment and retry (connectivity is intermittent)
2. Check if inverter is powered on
3. Verify network connectivity to 172.16.107.129
4. The system will automatically retry failed connections