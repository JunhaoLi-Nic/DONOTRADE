import axios from 'axios';
import { AuthService } from '../services/auth';

/**
 * This file provides compatibility utilities to replace Parse SDK functions
 * with our new MongoDB/FastAPI backend implementations.
 */

/**
 * Replacement for Parse.User.current()
 * Returns an object that mimics the Parse.User object
 */
export function getCurrentUser() {
    const user = AuthService.getCurrentUser();
    
    if (!user) {
        return null;
    }
    
    // Create a Parse-like user object
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
            // Update user profile
            try {
                const response = await axios.put('/api/user-profile', {
                    [key]: value
                });
                return response.data;
            } catch (error) {
                console.error('Error saving user:', error);
                throw error;
            }
        }
    };
}

/**
 * Replacement for Parse.User.logOut()
 */
export async function logOut() {
    try {
        await axios.post('/api/logout');
    } catch (error) {
        console.error('Error during logout API call:', error);
    }
    
    // Always clear local storage
    AuthService.logout();
    
    return Promise.resolve();
}

/**
 * Replacement for Parse.Object.extend()
 * @param {string} className - The name of the collection
 */
export function createObjectClass(className) {
    return {
        className,
        
        // Mock Query class
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
                        
                        const response = await axios.get(`/api/${className.toLowerCase()}?${params.toString()}`);
                        
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
                                    const response = await axios.put(`/api/${className.toLowerCase()}/${this.id}`, this.attributes);
                                    return response.data;
                                } catch (error) {
                                    console.error(`Error saving ${className}:`, error);
                                    throw error;
                                }
                            },
                            destroy: async function() {
                                try {
                                    await axios.delete(`/api/${className.toLowerCase()}/${this.id}`);
                                    return true;
                                } catch (error) {
                                    console.error(`Error deleting ${className}:`, error);
                                    throw error;
                                }
                            }
                        }));
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
                        const response = await axios.post(`/api/${className.toLowerCase()}`, this.attributes);
                        
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
    User: {
        current: getCurrentUser,
        logOut: logOut
    },
    
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