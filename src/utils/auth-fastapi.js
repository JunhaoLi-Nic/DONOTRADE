import axios from 'axios';
import { AuthService } from '../services/auth';

/**
 * This module provides a compatibility layer that looks like Parse API
 * but uses FastAPI directly, to make migration easier.
 */

// Mimic Parse.User functionality
const User = {
  // Get current user
  current: () => {
    const user = AuthService.getCurrentUser();
    
    if (!user) {
      return null;
    }
    
    // Create a Parse-like user object with get/set methods
    return {
      id: user.id || user._id,
      attributes: {
        ...user,
        objectId: user.id || user._id,
      },
      get: function(key) {
        return this.attributes[key];
      },
      set: function(key, value) {
        this.attributes[key] = value;
        return this;
      },
      save: async function() {
        // Update user profile via FastAPI
        try {
          const response = await axios.put('/api/user-profile', this.attributes);
          return response.data;
        } catch (error) {
          console.error('Error saving user:', error);
          throw error;
        }
      }
    };
  },
  
  // Logout user
  logOut: async () => {
    try {
      await AuthService.logout();
      return Promise.resolve();
    } catch (error) {
      console.error('Logout error:', error);
      return Promise.resolve(); // Always resolve to maintain compatibility
    }
  }
};

// Mimic Parse.Object functionality
function createObjectClass(className) {
  return {
    className,
    
    // Mock Query class for database queries
    Query: function() {
      return {
        className,
        constraints: {},
        _order: null,
        _skip: 0,
        _limit: 10,
        
        equalTo: function(key, value) {
          this.constraints[key] = value;
          return this;
        },
        
        descending: function(key) {
          this._order = `-${key}`;
          return this;
        },
        
        ascending: function(key) {
          this._order = key;
          return this;
        },
        
        skip: function(value) {
          this._skip = value;
          return this;
        },
        
        limit: function(value) {
          this._limit = value;
          return this;
        },
        
        find: async function() {
          try {
            // Build query params
            const params = new URLSearchParams();
            params.append('limit', this._limit);
            params.append('skip', this._skip);
            
            // Add constraints as params
            for (const [key, value] of Object.entries(this.constraints)) {
              if (key === 'user' && value?.id) {
                // Special case for user constraint
                // No need to add user_id since the API will handle this
              } else {
                params.append(key, value);
              }
            }
            
            // Add order param if set
            if (this._order) {
              params.append('order', this._order);
            }
            
            // Fix for _user endpoint - use user/profile instead
            let endpoint = typeof className === 'string' ? className.toLowerCase() : 
                           (className && className.className ? className.className.toLowerCase() : 'unknown');
            
            // Replace _user with user/profile
            if (endpoint === '_user') {
              endpoint = 'user/profile';
              console.log('Converting _user endpoint to user/profile');
            }
            
            // Try to make the request with proper endpoint
            try {
              const response = await axios.get(`/api/${endpoint}?${params.toString()}`);
              
              // Transform response to Parse-like objects
              return response.data.map(item => ({
                id: item.id || item._id,
                attributes: { ...item },
                get: function(key) {
                  return this.attributes[key];
                },
                set: function(key, value) {
                  this.attributes[key] = value;
                  return this;
                },
                save: async function() {
                  try {
                    // Fix for _user endpoint - use user/profile instead
                    let saveEndpoint = typeof className === 'string' ? className.toLowerCase() : 
                                 (className && className.className ? className.className.toLowerCase() : 'unknown');
                    
                    // Replace _user with user/profile
                    if (saveEndpoint === '_user') {
                      saveEndpoint = 'user/profile';
                    }
                    
                    const response = await axios.put(`/api/${saveEndpoint}/${this.id}`, this.attributes);
                    return response.data;
                  } catch (error) {
                    console.error(`Error saving ${className}:`, error);
                    throw error;
                  }
                },
                destroy: async function() {
                  try {
                    // Fix for _user endpoint - use user/profile instead
                    let deleteEndpoint = typeof className === 'string' ? className.toLowerCase() : 
                                     (className && className.className ? className.className.toLowerCase() : 'unknown');
                    
                    // Replace _user with user/profile
                    if (deleteEndpoint === '_user') {
                      deleteEndpoint = 'user/profile';
                    }
                    
                    await axios.delete(`/api/${deleteEndpoint}/${this.id}`);
                    return true;
                  } catch (error) {
                    console.error(`Error deleting ${className}:`, error);
                    throw error;
                  }
                }
              }));
            } catch (error) {
              // If the first attempt fails with 404, try alternative endpoints
              if (error.response && error.response.status === 404) {
                // Try common API pattern alternatives
                const alternatives = [
                  `${endpoint}s`, // plural form
                  `${endpoint.replace('_', '')}`, // without underscore
                  `user/${endpoint.replace('_', '')}` // under user namespace
                ];
                
                console.log(`Endpoint /api/${endpoint} failed, trying alternatives:`, alternatives);
                
                // Try each alternative
                for (const alt of alternatives) {
                  try {
                    console.log(`Trying alternative endpoint: /api/${alt}`);
                    const response = await axios.get(`/api/${alt}?${params.toString()}`);
                    
                    // If successful, save this endpoint for future use
                    localStorage.setItem(`endpoint_${endpoint}`, alt);
                    
                    // Return the transformed data
                    return response.data.map(item => ({
                      id: item.id || item._id,
                      attributes: { ...item },
                      get: function(key) {
                        return this.attributes[key];
                      },
                      set: function(key, value) {
                        this.attributes[key] = value;
                        return this;
                      }
                      // Other methods omitted for brevity
                    }));
                  } catch (altError) {
                    console.log(`Alternative endpoint /api/${alt} also failed:`, altError.message);
                  }
                }
              }
              
              // If we get here, all attempts failed
              console.error(`Error querying ${className}:`, error);
              throw error;
            }
          } catch (error) {
            console.error(`Error querying ${className}:`, error);
            throw error;
          }
        },
        
        first: async function() {
          // Limit to 1 result and return the first one
          this._limit = 1;
          const results = await this.find();
          return results.length > 0 ? results[0] : null;
        }
      };
    },
    
    // Constructor for new objects
    create: function(attributes = {}) {
      return {
        className,
        attributes,
        
        get: function(key) {
          return this.attributes[key];
        },
        
        set: function(key, value) {
          this.attributes[key] = value;
          return this;
        },
        
        setACL: function() {
          // ACLs are handled automatically by the backend
          return this;
        },
        
        save: async function() {
          try {
            // Ensure className is a string before calling toLowerCase
            const endpoint = typeof className === 'string' ? className.toLowerCase() : 
                            (className && className.className ? className.className.toLowerCase() : 'unknown');
            
            const response = await axios.post(`/api/${endpoint}`, this.attributes);
            
            // Update the object with the server response
            this.id = response.data.id || response.data._id;
            this.attributes = { ...response.data };
            
            return this;
          } catch (error) {
            console.error(`Error creating ${className}:`, error);
            throw error;
          }
        }
      };
    }
  };
}

// Export a Parse-like API
export default {
  User,
  
  Object: {
    extend: createObjectClass
  },
  
  Query: function(className) {
    return createObjectClass(className).Query();
  },
  
  ACL: function() {
    // No-op function for backward compatibility
    return {};
  }
}; 