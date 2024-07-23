import 'https://unpkg.com/@popperjs/core@2/dist/umd/popper.js';

const tooltip_triggers = document.querySelectorAll(".tooltip-trigger");

tooltip_triggers.forEach((trigger) => {
        const parent = trigger.parentElement;
        const label = trigger.getAttribute('aria-label');
        const tooltip_ = document.querySelector("#" + label);

        let placement = 'right';
        let fallbackPlacements = ['left', 'bottom'];
        const data_popper_placement = tooltip_.getAttribute('data-popper-placement');
        if (data_popper_placement === 'top') {
            placement = 'top';
            fallbackPlacements = ['bottom', 'right'];
        }
        if (data_popper_placement === 'left') {
            placement = 'left';
            fallbackPlacements = ['top', 'right'];
        }
        if (data_popper_placement === 'bottom') {
            placement = 'bottom';
            fallbackPlacements = ['top', 'right'];
        }

        const popperInstance = window.Popper.createPopper(trigger, tooltip_, {
            placement: placement,
            modifiers: [
                {
                    name: 'offset',
                    options: {
                        offset: [0, 20],
                    },
                },
                {
                    name: 'flip',
                    options: {
                        fallbackPlacements: fallbackPlacements,
                    },
                },
                {
                    name: "boundary",

                }
            ],
        });
        const show = () => {
            // Make the tooltip visible
            tooltip_.setAttribute('data-show', '');

            // Enable the event listeners
            popperInstance.setOptions((options) => ({
                ...options,
                modifiers: [
                    ...options.modifiers,
                    {name: 'eventListeners', enabled: true},
                ],
            }));

            // Update its position
            popperInstance.update();
        }

        const hide = () => {
            // Hide the tooltip
            tooltip_.removeAttribute('data-show');

            // Disable the event listeners
            popperInstance.setOptions((options) => ({
                ...options,
                modifiers: [
                    ...options.modifiers,
                    {name: 'eventListeners', enabled: false},
                ],
            }));
        }

        const showEvents = ['mouseenter', 'focus'];
        const hideEvents = ['mouseleave', 'blur'];

        showEvents.forEach((event) => {
                trigger.addEventListener(event, show);
            }
        );

        hideEvents.forEach((event) => {
                parent.addEventListener(event, hide);
            }
        );
    }
);
