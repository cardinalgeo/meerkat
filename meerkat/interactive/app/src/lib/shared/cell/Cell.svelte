<script lang="ts">
	import DynamicComponent from '$lib/shared/DynamicComponent.svelte';
	import type { CellInfo } from '$lib/utils/dataframe';
	import { createEventDispatcher } from 'svelte';
	import { setContext } from 'svelte/internal';
	import { writable } from 'svelte/store';

	export let data: any;
	export let cellInfo: CellInfo;
	export let cellComponent: string = '';
	export let cellProps: object = {};
	export let cellDataProp: string = 'data';
	export let editable: boolean = false;

	const dispatch = createEventDispatcher();
	setContext('cellEdit', (data: any) => {
		dispatch('edit', { value: data });
	});

	// need to actually create a new object, since we don't want to modify the
	// cell_props that were passed in
	$: {
		cellProps = { ...cellProps };
		cellProps[cellDataProp] = data;
		cellProps['cell_info'] = cellInfo;

		console.log("propaganda", cellProps)

		// iterate over cell_props and turn them into stores if they aren't already
		for (const [key, value] of Object.entries(cellProps)) {
			if ((value === null || value.subscribe === undefined) && !key.startsWith('on_')) {
				cellProps[key] = writable(value);
			}
		}
	}

	console.log("cellprops", cellProps)
</script>

<DynamicComponent name={cellComponent} props={{ ...cellProps, editable: writable(editable)}} />
