import React, { useState, useEffect, useCallback } from 'react';
import { Bell, XCircle, ExternalLink, Lock, Key, Database, Server, Globe } from 'lucide-react';
import { Alert, AlertDescription } from "./alert";

const NotificationComponent = ({ apiClient, auth }) => {
  const [deployments, setDeployments] = useState([]);
  const [viewedDeployments, setViewedDeployments] = useState(new Set());
  const [showDeployments, setShowDeployments] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchDeployments = useCallback(async () => {
    if (!apiClient) return;
    
    setLoading(true);
    try {
      const response = await apiClient.getGet({}, 
        {},
        { 
          headers: { 
            'Authorization': auth.user?.id_token,
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (response.data?.deployments) {
        setDeployments(response.data.deployments);
      }
    } catch (err) {
      console.error('Error fetching deployments:', err);
    } finally {
      setLoading(false);
    }
  }, [apiClient, auth.user?.id_token]);

  useEffect(() => {
    fetchDeployments();
    const interval = setInterval(fetchDeployments, 30000);
    return () => clearInterval(interval);
  }, [fetchDeployments]);

  const unviewedDeployments = deployments.filter(
    deployment => !viewedDeployments.has(deployment.session_id)
  );

  const toggleDeployments = () => {
    setShowDeployments(!showDeployments);
  };

  const handleCloseNotifications = () => {
    const newViewedDeployments = new Set(viewedDeployments);
    unviewedDeployments.forEach(deployment => newViewedDeployments.add(deployment.session_id));
    setViewedDeployments(newViewedDeployments);
    setShowDeployments(false);
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const getResourceIcon = (resourceType) => {
    switch (resourceType.toLowerCase()) {
      case 'rds':
        return <Database className="w-5 h-5 text-purple-600" />;
      case 'ec2':
        return <Server className="w-5 h-5 text-green-600" />;
      case 'ecs':
        return <Globe className="w-5 h-5 text-blue-600" />;
      case 'loadbalancer':
        return <Globe className="w-5 h-5 text-orange-600" />;
      case 'ssh_key':
        return <Key className="w-5 h-5 text-yellow-600" />;
      default:
        return '🔧';
    }
  };

  const ResourceCredentials = ({ resource }) => {
    const [showCredentials, setShowCredentials] = useState(false);

    if (!resource.username && !resource.password) return null;

    return (
      <div className="mt-2 p-2 bg-gray-50 rounded-md border border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Credentials</span>
          <button
            onClick={() => setShowCredentials(!showCredentials)}
            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
          >
            <Lock className="w-3 h-3" />
            {showCredentials ? 'Hide' : 'Show'} Credentials
          </button>
        </div>
        {showCredentials && (
          <div className="space-y-1 text-sm">
            {resource.username && (
              <div>
                <span className="font-medium">Username: </span>
                {resource.username}
              </div>
            )}
            {resource.password && (
              <div>
                <span className="font-medium">Password: </span>
                {resource.password}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const ResourceDetails = ({ resource }) => {
    const commonDetails = (
      <>
        <div>
          <span className="font-medium">Name: </span>
          {resource.resource_name}
        </div>
        {!resource.is_sensitive && resource.value && (
          <div>
            <span className="font-medium">Value: </span>
            {resource.value}
          </div>
        )}
      </>
    );

    switch (resource.type.toLowerCase()) {
      case 'rds':
        return (
          <div className="space-y-1 text-sm">
            {commonDetails}
            {resource.endpoint && (
              <div className="flex items-center gap-1">
                <span className="font-medium">Endpoint: </span>
                <span className="text-blue-600">{resource.endpoint}</span>
                <ExternalLink className="w-3 h-3 text-blue-600" />
              </div>
            )}
            <ResourceCredentials resource={resource} />
          </div>
        );

      case 'ec2':
        return (
          <div className="space-y-1 text-sm">
            {commonDetails}
            {resource.ip_address && (
              <div className="flex items-center gap-1">
                <span className="font-medium">IP Address: </span>
                <span className="text-blue-600">{resource.ip_address}</span>
                <ExternalLink className="w-3 h-3 text-blue-600" />
              </div>
            )}
          </div>
        );

      case 'ecs':
      case 'loadbalancer':
        return (
          <div className="space-y-1 text-sm">
            {commonDetails}
            {resource.dns_name && (
              <div className="flex items-center gap-1">
                <span className="font-medium">DNS: </span>
                <span className="text-blue-600">{resource.dns_name}</span>
                <ExternalLink className="w-3 h-3 text-blue-600" />
              </div>
            )}
          </div>
        );

      default:
        return <div className="space-y-1 text-sm">{commonDetails}</div>;
    }
  };

  return (
    <div className="relative">
      <button
        onClick={toggleDeployments}
        className="relative p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
      >
        <Bell className="w-6 h-6" />
        {unviewedDeployments.length > 0 && (
          <span className="absolute top-1 right-1 w-2 h-2 bg-blue-500 rounded-full" />
        )}
      </button>

      {showDeployments && (
        <div className="absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-xl border z-50">
          <div className="p-4 border-b flex justify-between items-center">
            <h3 className="font-semibold text-gray-700">New Deployments</h3>
            <button
              onClick={handleCloseNotifications}
              className="text-gray-400 hover:text-gray-600"
            >
              <XCircle className="w-5 h-5" />
            </button>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center">
                <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
              </div>
            ) : unviewedDeployments.length === 0 ? (
              <div className="p-4 text-center text-gray-500">
                No new deployments
              </div>
            ) : (
              <div className="p-2 space-y-2">
                {unviewedDeployments.map((deployment) => (
                  <Alert 
                    key={deployment.session_id} 
                    className="mb-0 bg-blue-50"
                  >
                    <div className="font-semibold mb-2 flex justify-between items-center">
                      <div className="text-sm text-gray-700">
                        Session ID: {deployment.session_id}
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatTimestamp(deployment.timestamp)}
                      </div>
                    </div>
                    <AlertDescription>
                      <div className="space-y-3">
                        {deployment.resources.map((resource, index) => (
                          <div 
                            key={resource.deployment_id} 
                            className={`p-3 rounded-md bg-white border ${
                              index !== deployment.resources.length - 1 ? 'mb-2' : ''
                            }`}
                          >
                            <div className="flex items-start justify-between mb-2">
                              <div className="flex items-center gap-2">
                                {getResourceIcon(resource.type)}
                                <span className="font-medium">{resource.type.toUpperCase()}</span>
                              </div>
                              <div className="text-xs text-gray-500">
                                ID: {resource.deployment_id}
                              </div>
                            </div>
                            <ResourceDetails resource={resource} />
                          </div>
                        ))}
                      </div>
                    </AlertDescription>
                  </Alert>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationComponent;