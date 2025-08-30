<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { pageId, timeZones, availableTags, tradeTags, legacy, registerOff } from '../stores/globals';
import { useGetCurrentUser, useGetPeriods, useGetTimeZone, useSetValues, useUpdateLegacy, useGetLegacy, checkParseAppId } from '../utils/utils';
import { useGetAvailableTags, useUpdateAvailableTags, useUpdateTags, useFindHighestIdNumber, useFindHighestIdNumberTradeTags } from '../utils/daily';
import { AuthService } from '../services/auth';
import axios from 'axios'

// Still check app ID for compatibility with frontend code expecting it
checkParseAppId();

const router = useRouter();
const signingUp = ref(false);
const errorMessage = ref('');
const registerOffFlag = ref(false);
const showRegisterForm = ref(false);

const loginForm = ref({
  email: '',
  password: '',
  timeZone: 'America/New_York'
});

// Check if registration is disabled
onMounted(async () => {
  try {
    console.log("GETTING REGISTER PAGE");
    const response = await axios.post('/api/registerPage');
    console.log("  --> Register page response:", response.data);
    // Only disable registration if we get an explicit true value
    registerOffFlag.value = response.data.registerOff === true;
    console.log("Register page status (disabled):", registerOffFlag.value);
    console.log("Register button should be visible:", !registerOffFlag.value);
    
    // Make sure Bootstrap is properly loaded
    if (window.bootstrap) {
      console.log("Bootstrap is available");
    } else {
      console.error("Bootstrap is not available - loading manually");
      // This is a safeguard but generally should not be needed
    }
  } catch (error) {
    console.error("Error getting register page status:", error);
    // Default to allowing registration if the endpoint fails
    registerOffFlag.value = false;
  }
});

// Handle user login
async function login() {
  console.log("\nLOGIN");
  errorMessage.value = '';
  signingUp.value = true;
  
  try {
    if (!loginForm.value.email || !loginForm.value.password) {
      errorMessage.value = 'Email and password are required';
      return;
    }
    
    // Set login timestamp to prevent login loop
    sessionStorage.setItem('last_login_attempt', Date.now().toString());
    
    await AuthService.login(loginForm.value.email, loginForm.value.password);
    console.log("Hooray! You are logged in");
    router.push('/dashboard');
  } catch (error) {
    errorMessage.value = error.message || 'Login failed. Please check your credentials.';
    console.error("Login error:", error);
  } finally {
    signingUp.value = false;
  }
}

// Handle user registration
async function register() {
  console.log("\nREGISTER");
  errorMessage.value = '';
  signingUp.value = true;
  
  try {
    if (!loginForm.value.email || !loginForm.value.password) {
      errorMessage.value = 'Email and password are required';
      return;
    }
    
    // Set login timestamp to prevent login loop
    sessionStorage.setItem('last_login_attempt', Date.now().toString());
    
    await AuthService.register({
      email: loginForm.value.email,
      username: loginForm.value.email,
      password: loginForm.value.password,
      timeZone: loginForm.value.timeZone
    });
    console.log("Hooray! Registration successful");
    router.push('/dashboard');
  } catch (error) {
    errorMessage.value = error.message || 'Registration failed. Please try again.';
    console.error("Registration error:", error);
  } finally {
    signingUp.value = false;
  }
}

async function updateSchema() {
  return new Promise((resolve, reject) => {
    console.log(" -> Updating schema")
    axios.post('/api/updateSchemas').then((response) => {
      //console.log("  --> Schema response "+JSON.stringify(response))
      existingSchema = response.data.existingSchema
      resolve(response)
    })
      .catch((error) => {
        console.log("Error get app id " + error);
        reject(error)
      });
  })
}

const checkLegacy = async (param) => {
  return new Promise(async (resolve, reject) => {
    console.log("\nCHECKING LEGACY")

    const updateAvailableTagsWithPatterns = async () => {
      return new Promise(async (resolve, reject) => {
        console.log("\nUpdate Available Tags With Patterns")
        const parseObject = Parse.Object.extend("patterns");
        const query = new Parse.Query(parseObject);
        const results = await query.find();
        if (results.length > 0) {
          for (let i = 0; i < results.length; i++) {
            const object = results[i];
            console.log(" -> Object id " + object.id)

            const highestIdNumberAvailableTags = useFindHighestIdNumber(availableTags);
            const highestIdNumberTradeTags = useFindHighestIdNumberTradeTags(tradeTags);

            function chooseHighestNumber(num1, num2) {
              return Math.max(num1, num2);
            }

            // Example usage:
            const highestIdNumber = chooseHighestNumber(highestIdNumberAvailableTags, highestIdNumberTradeTags);

            //console.log(" -> Highest tag id number " + highestIdNumber);
            let temp = {}
            temp.id = "tag_" + (highestIdNumber + 1).toString()
            temp.name = object.get("name")
            tradeTags.push(temp)
          }
          resolve()
        } else {
          alert("Updating trade tags did not return any results")
        }
      })
    }

    const updateAvailableTagsWithMistakes = async () => {
      return new Promise(async (resolve, reject) => {
        console.log("\nUpdate Available Tags With Mistakes")
        const parseObject = Parse.Object.extend("mistakes");
        const query = new Parse.Query(parseObject);
        const results = await query.find();
        if (results.length > 0) {
          for (let i = 0; i < results.length; i++) {
            const object = results[i];
            console.log(" -> Object id " + object.id)
            const highestIdNumberAvailableTags = useFindHighestIdNumber(availableTags);
            const highestIdNumberTradeTags = useFindHighestIdNumberTradeTags(tradeTags);

            function chooseHighestNumber(num1, num2) {
              return Math.max(num1, num2);
            }

            // Example usage:
            const highestIdNumber = chooseHighestNumber(highestIdNumberAvailableTags, highestIdNumberTradeTags);

            //console.log(" -> Highest tag id number " + highestIdNumber);
            let temp = {}
            temp.id = "tag_" + (highestIdNumber + 1).toString()
            temp.name = object.get("name")
            tradeTags.push(temp)

          }
          resolve()
        } else {
          alert("Updating trade tags did not return any results")
        }
      })
    }

    const updateAvailableTags = async () => {
      console.log("\n -> Handling available tags legacy")
      await useGetAvailableTags()
      if (existingSchema.includes("patterns")) await updateAvailableTagsWithPatterns()
      if (existingSchema.includes("mistakes")) await updateAvailableTagsWithMistakes()
      //console.log(" --> Trade Tags " + JSON.stringify(tradeTags))
      await useUpdateAvailableTags()
      await useUpdateLegacy("updateAvailableTagsWithPatterns")
    }

    const updateTags = async () => {
      console.log("\n -> Handling tags legacy")
      await useGetAvailableTags()
      if (existingSchema.includes("setups")) await copySetups()
      await useUpdateLegacy("updateSetupsToTags")
    }

    const copySetups = async () => {
      return new Promise(async (resolve, reject) => {
        const parseObject = Parse.Object.extend("setups");
        const query = new Parse.Query(parseObject);
        query.include('pattern');
        query.include('mistake');
        const results = await query.find();

        if (results.length > 0) {
          for (let i = 0; i < results.length; i++) {
            let setupsArray = []
            const object = results[i];
            console.log(" -> Object id " + object.id)

            //console.log(" -> Object " + JSON.stringify(object))
            let index1 = availableTags.findIndex(obj => obj.id == "group_0")

            const createTemp = async (param) => {
              let index2 = availableTags[index1].tags.findIndex(obj => obj.name == param)
              if (index2 != -1) {
                setupsArray.push(availableTags[index1].tags[index2])
              } else {
                console.log(" -> Error : cannot find " + param + " in availableTags")
              }
            }

            if (object.get('pattern') != null && object.get('pattern') != '') {
              let name = object.get('pattern').get('name')
              console.log("  --> Pattern name " + name)
              createTemp(name)
            }

            if (object.get('mistake') != null && object.get('mistake') != '') {
              let name = object.get('mistake').get('name')
              console.log("  --> mistake name " + name)
              createTemp(name)
            }
            console.log("   ----> setupsArray " + JSON.stringify(setupsArray))

            //Saving to tags
            if (setupsArray.length > 0) {

              const parseObject = Parse.Object.extend("tags");
              const object2 = new parseObject();
              object2.set("user", Parse.User.current())
              object2.set("tags", setupsArray)
              object2.set("dateUnix", object.get('dateUnix'))
              object2.set("tradeId", object.get('tradeId'))
              object2.setACL(new Parse.ACL(Parse.User.current()));
              object2.save()
                .then(async (object) => {
                  console.log(' -> Added new tags with id ' + object.id)
                }, (error) => {
                  console.log('Failed to create new object, with error code: ' + error.message);
                })
            }
          }
          resolve()

        } else {
          console.log(" -> No setups to copy")
          resolve()
        }
      })
    }

    const copyNotes = async () => {
      return new Promise(async (resolve, reject) => {
        const parseObject = Parse.Object.extend("setups");
        const query = new Parse.Query(parseObject);
        const results = await query.find();
        if (results.length > 0) {
          for (let i = 0; i < results.length; i++) {
            let setupsArray = []
            const object = results[i];
            console.log(" -> Object id " + object.id)


            //Saving to notes
            if (object.get('note') != undefined && object.get('note') != '') {

              const parseObject = Parse.Object.extend("notes");
              const object2 = new parseObject();
              object2.set("user", Parse.User.current())
              object2.set("note", object.get('note'))
              object2.set("dateUnix", object.get('dateUnix'))
              object2.set("tradeId", object.get('tradeId'))
              object2.setACL(new Parse.ACL(Parse.User.current()));
              object2.save()
                .then(async (object) => {
                  console.log(' -> Added new note with id ' + object.id)
                }, (error) => {
                  console.log('Failed to create new object, with error code: ' + error.message);
                })
            }
          }
          resolve()

        } else {
          console.log(" -> No notes to copy")
          resolve()
        }
      })
    }

    const updateNotes = async () => {
      console.log("\n -> Handling notes legacy")
      if (existingSchema.includes("setups")) await copyNotes()
      await useUpdateLegacy("updateNotes")
    }

    const updateTagsArray = async () => {
      return new Promise(async (resolve, reject) => {
        console.log("\n -> Handling tags json legacy")

        const copyTagsToArray = async () => {
          return new Promise(async (resolve, reject) => {
            const parseObject = Parse.Object.extend("tags");
            const query = new Parse.Query(parseObject);
            const results = await query.find();
            if (results.length > 0) {
              for (let i = 0; i < results.length; i++) {
                const object = results[i];
                console.log(" -> Object id " + object.id)

                if (object.get('tags') != undefined && object.get('tags').length > 0) {
                  let tagsArray = []
                  for (let index = 0; index < object.get('tags').length; index++) {
                    const element = object.get('tags')[index];
                    tagsArray.push(element.id)
                  }
                  object.set("tags", tagsArray)
                  object.save()
                    .then(async (object) => {
                      console.log(' -> Updated tags to array with id ' + object.id)
                    }, (error) => {
                      console.log(' -> Failed to update tags to array, with error code: ' + error.message);
                    })
                }
              }
              resolve()

            } else {
              console.log(" -> No tags to update")
              resolve()
            }
          })
        }

        if (existingSchema.includes("tags")) {
          await copyTagsToArray()
        }
        await useUpdateLegacy("updateTagsArray")
        resolve()
      })
    }

    const copyDiary = async () => {
      return new Promise(async (resolve, reject) => {
        const parseObject = Parse.Object.extend("diaries");
        const query = new Parse.Query(parseObject);
        const results = await query.findAll(); // findAll gets all (limited to 1000 instead of default 100)
        if (results.length > 0) {
          for (let i = 0; i < results.length; i++) {
            let setupsArray = []
            const object = results[i];
            //console.log(" -> Object id " + object.id)


            //Saving to notes
            if (object.get('journal') != undefined && object.get('journal') != '') {

              object.set("diary", Object.values(object.get('journal')).join(''))
              object.save()
                .then(async (object) => {
                  console.log(' -> Updated diary with id ' + object.id)
                }, (error) => {
                  console.log('Failed to create new diary, with error code: ' + error.message);
                })
            }
          }
          resolve()

        } else {
          console.log(" -> No diary to copy")
          resolve()
        }
      })
    }

    const updateDiary = async () => {
      console.log("\n -> Handling diary legacy")
      await copyDiary()
      await useUpdateLegacy("updateDiary")
    }

    await useGetLegacy()

    if (legacy == undefined || legacy.length == 0) {
      await updateAvailableTags()
      await updateTags()
      await updateNotes()
      await updateTagsArray()
      await updateDiary()
    }

    else if (legacy.length > 0) {
      let index1 = legacy.findIndex(obj => obj.name == "updateAvailableTagsWithPatterns")
      if (index1 == -1) {
        await updateAvailableTags()
      } else {
        console.log("  --> Legacy 'updateAvailableTags' done")
      }

      let index2 = legacy.findIndex(obj => obj.name == "updateSetupsToTags")
      if (index2 == -1) {
        await updateTags()
      } else {
        console.log("  --> Legacy 'updateSetupsToTags' done")
      }

      let index3 = legacy.findIndex(obj => obj.name == "updateNotes")
      if (index3 == -1) {
        await updateNotes()
      } else {
        console.log("  --> Legacy 'updateNotes' done")
      }

      let index4 = legacy.findIndex(obj => obj.name == "updateTagsArray")
      if (index4 == -1) {
        await updateTagsArray()
      } else {
        console.log("  --> Legacy 'updateTagsArray' done")
      }

      let index5 = legacy.findIndex(obj => obj.name == "updateDiary")
      if (index5 == -1) {
        await updateDiary()
      } else {
        console.log("  --> Legacy 'updateDiary' done")
      }

    } else {
      console.log(" -> There is an issue with legacy")
    }
    resolve()
  })
}


</script>

<template>
  <div class="container-fluid">
    <!-- Start Page Content here -->
    <div class="content-page">
      <div class="content">
        <div class="container-fluid container-login">
          <div class="row justify-content-center">
            <div class="col-md-8 col-lg-6 col-xl-5">
              <div class="card mt-md-5">
                <div class="card-body p-4">
                  <div class="text-center">
                    <img src="../assets/logo.svg" alt="Logo" class="mb-3" width="200">
                    <h4 class="mt-2 mb-4">TradeNote</h4>
                  </div>
                  
                  <!-- Login Form -->
                  <div v-if="!showRegisterForm">
                    <h5 class="text-center mb-4">Login to your account</h5>
                    <form @submit.prevent="login" id="loginForm">
                      <div class="mb-3">
                        <label for="emailaddress" class="form-label">Email address</label>
                        <input class="form-control" type="email" id="emailaddress" required=""
                          placeholder="Enter your email" v-model="loginForm.email">
                      </div>

                      <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input class="form-control" type="password" required="" id="password"
                          placeholder="Enter your password" v-model="loginForm.password">
                      </div>

                      <div class="mb-3">
                        <div class="form-check">
                          <input type="checkbox" class="form-check-input" id="checkbox-signin">
                          <label class="form-check-label" for="checkbox-signin">Remember me</label>
                        </div>
                      </div>

                      <div class="mb-0 text-center d-grid">
                        <button class="btn btn-primary" type="submit" :disabled="signingUp">
                          <span v-if="signingUp" class="spinner-border spinner-border-sm" role="status"
                            aria-hidden="true"></span>
                          <span v-if="signingUp">Logging in...</span>
                          <span v-else>Log In</span>
                        </button>
                      </div>
                      
                      <div class="mt-3 text-center" v-if="!registerOffFlag">
                        <p>Don't have an account? <a href="#" @click.prevent="showRegisterForm = true" class="text-primary fw-bold">Register now</a></p>
                      </div>

                      <div v-if="errorMessage" class="alert alert-danger mt-3">
                        {{ errorMessage }}
                      </div>
                    </form>
                  </div>
                  
                  <!-- Register Form -->
                  <div v-else>
                    <h5 class="text-center mb-4">Create an account</h5>
                    <form @submit.prevent="register" id="registerForm">
                      <div class="mb-3">
                        <label for="emailaddress-register" class="form-label">Email address</label>
                        <input class="form-control" type="email" id="emailaddress-register" required=""
                          placeholder="Enter your email" v-model="loginForm.email">
                      </div>

                      <div class="mb-3">
                        <label for="password-register" class="form-label">Password</label>
                        <input class="form-control" type="password" required="" id="password-register"
                          placeholder="Enter your password" v-model="loginForm.password">
                      </div>

                      <div class="mb-3">
                        <label for="timeZone" class="form-label">Time Zone</label>
                        <select class="form-select" id="timeZone" v-model="loginForm.timeZone">
                          <option value="America/New_York">New York (EDT/EST)</option>
                          <option value="America/Chicago">Chicago (CDT/CST)</option>
                          <option value="America/Denver">Denver (MDT/MST)</option>
                          <option value="America/Los_Angeles">Los Angeles (PDT/PST)</option>
                          <option value="Europe/London">London (BST/GMT)</option>
                          <option value="Europe/Paris">Paris (CEST/CET)</option>
                          <option value="Asia/Tokyo">Tokyo (JST)</option>
                          <option value="Australia/Sydney">Sydney (AEDT/AEST)</option>
                        </select>
                      </div>

                      <div class="mb-0 text-center d-grid">
                        <button class="btn btn-primary" type="submit" :disabled="signingUp">
                          <span v-if="signingUp" class="spinner-border spinner-border-sm" role="status"
                            aria-hidden="true"></span>
                          <span v-if="signingUp">Creating account...</span>
                          <span v-else>Register</span>
                        </button>
                      </div>
                      
                      <div class="mt-3 text-center">
                        <p>Already have an account? <a href="#" @click.prevent="showRegisterForm = false" class="text-primary fw-bold">Log in</a></p>
                      </div>

                      <div v-if="errorMessage" class="alert alert-danger mt-3">
                        {{ errorMessage }}
                      </div>
                    </form>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>