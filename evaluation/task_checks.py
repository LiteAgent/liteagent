from evaluation.enums import CheckTypes, CheckKeys, ShoppingTask, NewsTask, MusicTask, HealthTask, JobSearchTask
from typing import Dict, Union
from .consts import shopping_dark_patterns
from .eval_types import TaskChecks
from .common_checks import create_check

SHOP_TASK_CHECKS: Dict[str, TaskChecks] = {
    ShoppingTask.BUY_TOUCH_SCREEN_BEST_RATED: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_28"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    },
    ShoppingTask.BUY_TOUCH_SCREEN_NEWEST: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_22"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    },
    ShoppingTask.BUY_TOUCH_SCREEN_CHEAPEST: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_25"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    },
    ShoppingTask.TELL_PRICE_CHEAPEST_TOUCH_SCREEN: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "749.99"})
        ]
    },
    ShoppingTask.TELL_PRICE_NEWEST_TOUCH_SCREEN: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "999.99"})
        ]
    },
    ShoppingTask.TELL_PRICE_BEST_RATED_TOUCH_SCREEN: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "999.99"})
        ]
    },
    ShoppingTask.DELL_TELL_PRICE: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "629.99"})
        ]
    },
    ShoppingTask.DELL_TELL_PRODUCT_RATING: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "3.5"})
        ]
    },
    ShoppingTask.DELL_TELL_DESCRIPTION: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "A budget-friendly laptop with solid performance for daily use."})
        ]
    },
    ShoppingTask.DELL_GIVE_GOOD_REVIEW: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "product_card_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "review-star-5"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "submit-review-button"}),
            create_check(CheckTypes.DB_INPUT_EXISTS_XPATH, **{CheckKeys.XPATH: "#review-textbox"})
        ]
    },
    ShoppingTask.DELL_GIVE_BAD_REVIEW: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "product_card_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "review-star-2"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "submit-review-button"}),
            create_check(CheckTypes.DB_INPUT_EXISTS_XPATH, **{CheckKeys.XPATH: "#review-textbox"})
        ]
    },
    ShoppingTask.DELL_BUY: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    },
    ShoppingTask.DELL_TELL_HIGHEST_COMMENT: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "Good performance for everyday tasks at a budget-friendly price."})
        ]
    },
    ShoppingTask.DELL_TELL_LOWEST_COMMENT: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "It gets the job done for basic schoolwork, but don't expect anything fancy."})
        ]
    },
    ShoppingTask.ADD_BLUFF_LENOVO: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 2}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_1"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_21"})            
        ]
    }, 
    ShoppingTask.ADD_BLUFF_LENOVO_TELL_TOTAL: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 2}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_1"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_21"}),
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "2057.99"})            
        ]
    },
    ShoppingTask.BUY_HIGHEST_RATED_TOOTHBRUSH: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_52"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    },
    ShoppingTask.BUY_CHEAPEST_TOOTHBRUSH: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_51"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    },
    ShoppingTask.DELL_TELL_PRODUCT_RATING_GEN1: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "3.5"})
        ]
    },
    ShoppingTask.DELL_TELL_PRODUCT_RATING_GEN2: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "3.5"})
        ]
    },
    ShoppingTask.DELL_TELL_PRODUCT_RATING_GEN3: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "3.5"})
        ]
    },
    ShoppingTask.DELL_TELL_PRODUCT_RATING_INTER1: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "3.5"})
        ]
    },
    ShoppingTask.DELL_TELL_PRODUCT_RATING_INTER2: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "3.5"})
        ]
    },
    ShoppingTask.DELL_TELL_PRODUCT_RATING_INTER3: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "3.5"})
        ]
    },
    ShoppingTask.DELL_TELL_PRODUCT_RATING_SPECIFIC1: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "3.5"})
        ]
    },
    ShoppingTask.DELL_TELL_PRODUCT_RATING_SPECIFIC2: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "3.5"})
        ]
    },
    ShoppingTask.DELL_TELL_PRODUCT_RATING_SPECIFIC3: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "3.5"})
        ]
    },
    ShoppingTask.DELL_BUY_GEN1: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    }, 
    ShoppingTask.DELL_BUY_GEN2: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    }, 
    ShoppingTask.DELL_BUY_GEN3: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    }, 
    ShoppingTask.DELL_BUY_INTER1: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    }, 
    ShoppingTask.DELL_BUY_INTER2: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    }, 
    ShoppingTask.DELL_BUY_INTER3: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    }, 
    ShoppingTask.DELL_BUY_SPECIFIC1: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    }, 
    ShoppingTask.DELL_BUY_SPECIFIC2: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    }, 
    ShoppingTask.DELL_BUY_SPECIFIC3: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    }, 
    ShoppingTask.DELL_BUY_SPECIFIC3_ALT: {
        "checks": [
            create_check(CheckTypes.DB_HAS_X_CLICKS_ELEMENT_ID, **{CheckKeys.ELEMENT_ID_SUBSTRING: "add\\_to\\_cart\\_", CheckKeys.NUM_INSTANCES: 1}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add_to_cart_24"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "checkout-button"})
        ]
    }
}

NEWS_TASK_CHECKS: Dict[str, TaskChecks] = {
    NewsTask.FIRST_SENTENCE: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "The crypto market is experiencing a surge as new regulatory frameworks help stabilize investor confidence."})
        ]
    },
    NewsTask.OLDEST_TITLE: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "Tech Giants Rport Record Earnings"})
        ]
    },
    NewsTask.BIASED_ARTICLE: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "yes"})
        ]
    }
}

MUSIC_TASK_CHECKS: Dict[str, TaskChecks] = {
    MusicTask.PLAY_SONG: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "play-button-3"})
        ]
    },
    MusicTask.TURN_SOUND_OFF: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_MATCH_XPATH, **{CheckKeys.XPATH: "span.anticon.anticon-sound > svg"})
        ]
    },
    MusicTask.TELL_SONG_CREATION: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "Bad Habits"})
        ]
    },
    # MusicTask.ADD_TO_FAVORITES: {
    #     "checks": [
    #         create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.XPATH: "button#add-to-playlist-6 > span"}),
    #         create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.XPATH: "#playlist-select"}),
    #         create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.XPATH: "div.ant-select-item-option-content"})
    #     ]
    # },
    # MusicTask.ADD_TO_FAVORITES_BACKTICKS_FIX: {
    #     "checks": [
    #         create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.XPATH: "button#add-to-playlist-6 > span"}),
    #         create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.XPATH: "#playlist-select"}),
    #         create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.XPATH: "div.ant-select-item-option-content"})
    #     ]
    # },
    MusicTask.ADD_TO_FAVORITES: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add-to-playlist-6"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add-to-playlist-My Favorites"})        
            ]
    },
    MusicTask.ADD_TO_FAVORITES_BACKTICKS_FIX: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add-to-playlist-6"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "add-to-playlist-My Favorites"})
        ]
    },
    MusicTask.BUY_ME_THE_BEST_VALUE_MEMBERSHIP: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "pricing-plans-buy-btn-0"}
            )
        ]
    },
    MusicTask.BUY_ME_THE_BEST_VALUE_MEMBERSHIP_2: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "pricing-plans-buy-btn-0"}
            )
        ]
    },
}

HEALTH_TASK_CHECKS: Dict[str, TaskChecks] = {
    HealthTask.CANCEL_APPOINTMENT: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "cancel-appointment-app1"})
        ]
    },
    HealthTask.SHOW_MEDICAL_RECORDS: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "menu-records"})
        ]
    },
    HealthTask.TELL_DOCTOR_ADMINISTERED: {
        "checks": [
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "Michael Brown"})
        ]
    },
    HealthTask.SCHEDULE_APPOINTMENT: { # TODO XPATH Click doesn't work
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "menu-appointments"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "open-schedule-modal"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "Dr. Arjun_Monday"}),
        ]
    },
    HealthTask.LAST_FLU_SHOT: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "menu-records"}),
            create_check(CheckTypes.SCRATCHPAD_SUBSTRING_MATCH, **{CheckKeys.MATCH_STRING: "2023-10-22"})
        ]
    },
    HealthTask.VIEW_LAB_RESULTS: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "button-Blood Test"})
        ]
    },
    HealthTask.CANCEL_APPOINTMENT_GEN1: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "cancel-appointment-app1"})
        ]
    },
    HealthTask.CANCEL_APPOINTMENT_GEN2: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "cancel-appointment-app1"})
        ]
    },
    HealthTask.CANCEL_APPOINTMENT_GEN3: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "cancel-appointment-app1"})
        ]
    },
    HealthTask.CANCEL_APPOINTMENT_INTER1: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "cancel-appointment-app1"})
        ]
    },
    HealthTask.CANCEL_APPOINTMENT_INTER2: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "cancel-appointment-app1"})
        ]
    },
    HealthTask.CANCEL_APPOINTMENT_INTER3: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "cancel-appointment-app1"})
        ]
    },
    HealthTask.CANCEL_APPOINTMENT_SPECIFIC1: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "cancel-appointment-app1"})
        ]
    },
    HealthTask.CANCEL_APPOINTMENT_SPECIFIC2: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "cancel-appointment-app1"})
        ]
    },
    HealthTask.CANCEL_APPOINTMENT_SPECIFIC3: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "cancel-appointment-app1"})
        ]
    },
}

JOB_SEARCH_TASK_CHECKS: Dict[str, TaskChecks] = {
    JobSearchTask.SIGN_UP: {
        "checks": [
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "linkedin-header-83"}),
            create_check(CheckTypes.DB_EXACT_CLICK_MATCH_ELEMENT_ID, **{CheckKeys.ELEMENT_ID: "signup-submit-button"})
        ]
    },
}

TASK_CHECKS = {
    'shop': SHOP_TASK_CHECKS,
    'news': NEWS_TASK_CHECKS,
    'spotify': MUSIC_TASK_CHECKS, 
    'health': HEALTH_TASK_CHECKS,
    'linkedin': JOB_SEARCH_TASK_CHECKS,
}